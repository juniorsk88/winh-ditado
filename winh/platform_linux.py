"""Camada do Linux (X11): atalho global, digitacao e instancia unica."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

_errors: list[str] = []

try:
    from Xlib import X, XK, display
    from Xlib.ext import xtest
except Exception as failure:  # pragma: no cover - depende do sistema
    X = XK = display = xtest = None
    _errors.append(str(failure))

MOD_MAP = {
    "win": "Mod4",
    "super": "Mod4",
    "ctrl": "Control",
    "control": "Control",
    "alt": "Mod1",
    "shift": "Shift",
}


def available() -> tuple[bool, str]:
    if display is None:
        return False, "python-xlib não está instalado"
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" and not os.environ.get("DISPLAY"):
        return False, "sessão Wayland sem X11: atalho global e digitação não funcionam"
    try:
        probe = display.Display()
        probe.close()
    except Exception as failure:
        return False, f"não consegui abrir o X11: {failure}"
    return True, ""


def parse_hotkey(spec: str) -> tuple[int, str]:
    parts = [part.strip().lower() for part in str(spec or "win+h").split("+") if part.strip()]
    mods = 0
    key = parts[-1] if parts else "h"
    for part in parts[:-1]:
        name = MOD_MAP.get(part)
        if name:
            mods |= getattr(X, f"{name}Mask")
    return mods, key


class Hotkey:
    def __init__(self, spec: str, callback, log) -> None:
        self.spec = spec
        self.callback = callback
        self.log = log
        self.ok = False
        self.error = ""
        self._thread: threading.Thread | None = None
        self._display = None
        self._ready = threading.Event()

    def start(self) -> bool:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        return self.ok

    def _run(self) -> None:
        try:
            mods, key = parse_hotkey(self.spec)
            self._display = display.Display()
            root = self._display.screen().root
            keysym = XK.string_to_keysym(key)
            keycode = self._display.keysym_to_keycode(keysym)
            root.grab_key(keycode, mods, True, X.GrabModeAsync, X.GrabModeAsync)
            self._display.sync()
            self.ok = True
            self._ready.set()
        except Exception as failure:
            self.error = f"não consegui registrar {self.spec}: {failure}"
            self._ready.set()
            return
        try:
            while True:
                event = self._display.next_event()
                if event.type == X.KeyPress:
                    try:
                        self.callback()
                    except Exception as failure:
                        self.log.exception("erro no atalho: %s", failure)
        except Exception:
            pass

    def stop(self) -> None:
        try:
            if self._display is not None:
                self._display.close()
        except Exception:
            pass


def _spare_keycode(d) -> int:
    mapping = d.get_keyboard_mapping(8, 248)
    for offset, syms in enumerate(mapping):
        if not any(syms):
            return 8 + offset
    return 250


def type_text(text: str, delay_ms: int = 10) -> None:
    """Digita via XTEST, remapeando um keycode livre para cada caractere."""
    d = display.Display()
    spare = _spare_keycode(d)
    pause = max(0, int(delay_ms)) / 1000.0
    try:
        for ch in text:
            if ch == "\r":
                continue
            if ch == "\n":
                keysym = XK.string_to_keysym("Return")
            else:
                code = ord(ch)
                keysym = code if code < 0x100 else 0x01000000 + code
            d.change_keyboard_mapping(spare, [(keysym, keysym, keysym, keysym)])
            d.sync()
            xtest.fake_input(d, X.KeyPress, spare)
            xtest.fake_input(d, X.KeyRelease, spare)
            d.sync()
            time.sleep(pause)
    finally:
        try:
            d.change_keyboard_mapping(spare, [(0, 0, 0, 0)])
            d.sync()
        except Exception:
            pass
        d.close()


def foreground_title() -> str:
    try:
        d = display.Display()
        root = d.screen().root
        prop = root.get_full_property(d.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
        if prop and prop.value:
            window = d.create_resource_object("window", prop.value[0])
            name = window.get_wm_name()
            d.close()
            return name or "(sem título)"
        d.close()
    except Exception:
        pass
    return "(desconhecida)"


def single_instance() -> bool:
    import fcntl

    path = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / "winh-ditado.lock"
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    handle.write(str(os.getpid()))
    handle.flush()
    globals()["_lock_handle"] = handle  # mantem o lock vivo
    return True


def install_autostart(exe: str, args: str = "") -> None:
    path = Path.home() / ".config" / "autostart" / "winh-ditado.desktop"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Winh Ditado\n"
        f"Exec={exe} {args}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n",
        encoding="utf-8",
    )


def remove_autostart() -> None:
    (Path.home() / ".config" / "autostart" / "winh-ditado.desktop").unlink(missing_ok=True)

def beep(kind: str = "start", enabled: bool = True) -> None:
    """Som curto de retorno usando o primeiro tocador disponivel."""
    if not enabled:
        return
    import shutil
    import subprocess

    candidates = [
        ["canberra-gtk-play", "-i", "audio-volume-change"],
        ["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
        ["aplay", "-q", "/usr/share/sounds/alsa/Front_Center.wav"],
    ]
    for command in candidates:
        if shutil.which(command[0]):
            try:
                subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue

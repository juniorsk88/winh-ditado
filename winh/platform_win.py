"""Camada do Windows: atalho global, digitacao e instancia unica."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1
ERROR_ALREADY_EXISTS = 183

VK_CODES = {
    "win": 0x5B,
    "super": 0x5B,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _UNION)]


def _key(w_vk: int, w_scan: int, flags: int) -> INPUT:
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = KEYBDINPUT(w_vk, w_scan, flags, 0, None)
    return item


def send_inputs(items: list[INPUT]) -> None:
    if not items:
        return
    array = (INPUT * len(items))(*items)
    if user32.SendInput(len(items), array, ctypes.sizeof(INPUT)) != len(items):
        raise OSError(ctypes.get_last_error(), "SendInput falhou")


def type_text(text: str, delay_ms: int = 10) -> None:
    """Digita o texto na janela em foco, caractere por caractere."""
    pause = max(0, int(delay_ms)) / 1000.0
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            send_inputs([_key(0x0D, 0, 0), _key(0x0D, 0, KEYEVENTF_KEYUP)])
        else:
            code = ord(ch)
            if code > 0xFFFF:
                encoded = ch.encode("utf-16-le")
                for index in range(0, len(encoded), 2):
                    unit = int.from_bytes(encoded[index : index + 2], "little")
                    send_inputs([_key(0, unit, KEYEVENTF_UNICODE), _key(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)])
            else:
                send_inputs([_key(0, code, KEYEVENTF_UNICODE), _key(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)])
        time.sleep(pause)


def foreground_title() -> str:
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "(nenhuma janela)"
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buffer, 256)
        return buffer.value or f"(janela {hwnd})"
    except Exception:
        return "(desconhecida)"


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'win+h' -> (modificadores, virtual-key)."""
    parts = [part.strip().lower() for part in str(spec or "win+h").split("+") if part.strip()]
    mods = 0
    key = parts[-1] if parts else "h"
    for part in parts[:-1]:
        if part in ("win", "super"):
            mods |= MOD_WIN
        elif part in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif part == "alt":
            mods |= MOD_ALT
        elif part == "shift":
            mods |= MOD_SHIFT
    if len(key) == 1:
        vk = ord(key.upper())
    else:
        vk = VK_CODES.get(key, 0x48)
    return mods | MOD_NOREPEAT, vk


class Hotkey:
    """Registra o atalho global e chama o callback no seu proprio loop."""

    def __init__(self, spec: str, callback, log) -> None:
        self.spec = spec
        self.callback = callback
        self.log = log
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self.ok = False
        self.error = ""

    def start(self) -> bool:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        return self.ok

    def _run(self) -> None:
        mods, vk = parse_hotkey(self.spec)
        if not user32.RegisterHotKey(None, 0xB1, mods, vk):
            self.error = f"não consegui registrar {self.spec} (erro {ctypes.get_last_error()})"
            self._ready.set()
            return
        self.ok = True
        self._ready.set()
        message = wintypes.MSG()
        try:
            while True:
                got = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if got == 0 or got == -1:
                    break
                if message.message == WM_HOTKEY:
                    try:
                        self.callback()
                    except Exception as failure:
                        self.log.exception("erro no atalho: %s", failure)
                else:
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
        finally:
            user32.UnregisterHotKey(None, 0xB1)

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            try:
                user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass


def single_instance() -> bool:
    kernel32.CreateMutexW(None, False, "Global\\WinhDitado")
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def instance_exists() -> bool:
    kernel32.CreateMutexW(None, False, "Global\\WinhDitado")
    return ctypes.get_last_error() == ERROR_ALREADY_EXISTS


def install_autostart(exe: str, args: str = "") -> None:
    import winreg

    command = f'"{exe}" {args}'.strip()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "WinhDitado", 0, winreg.REG_SZ, command)


def remove_autostart() -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, "WinhDitado")
    except Exception:
        pass

def beep(kind: str = "start", enabled: bool = True) -> None:
    """Som curto de retorno (nao bloqueia o ditado)."""
    if not enabled:
        return
    try:
        import winsound

        pattern = {
            "start": [(880, 70)],
            "stop": [(660, 60), (440, 90)],
            "done": [(1046, 45)],
            "error": [(320, 130), (240, 160)],
        }.get(kind, [])
        for freq, ms in pattern:
            winsound.Beep(freq, ms)
    except Exception:
        pass

"""Ícone na bandeja do sistema: a porta de entrada visual do programa."""

from __future__ import annotations

import threading


def _image():
    from PIL import Image, ImageDraw

    try:
        from . import config

        for name in ("winh-ditado.ico", "winh-ditado.png"):
            path = config.app_root() / name
            if path.exists():
                return Image.open(path).convert("RGBA").resize((64, 64), Image.LANCZOS)
    except Exception:
        pass

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, 61, 61), fill=(179, 38, 30, 255))
    draw.rounded_rectangle((26, 12, 38, 36), radius=6, fill=(255, 255, 255, 255))
    draw.arc((18, 22, 46, 48), start=0, end=180, fill=(255, 255, 255, 255), width=4)
    draw.line((32, 46, 32, 53), fill=(255, 255, 255, 255), width=4)
    draw.line((22, 53, 42, 53), fill=(255, 255, 255, 255), width=4)
    return img


class Tray:
    def __init__(self, on_settings, on_toggle, on_quit, on_game=None, on_game_off=None) -> None:
        self.on_settings = on_settings
        self.on_game = on_game
        self.on_game_off = on_game_off
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        try:
            import pystray
        except Exception:
            return False
        menu = pystray.Menu(
            pystray.MenuItem("Configurações…", lambda: self._call(self.on_settings), default=True),
            pystray.MenuItem("Pausar / retomar", lambda: self._call(self.on_toggle)),
            pystray.MenuItem("Modo jogo (liberar memória)", lambda: self._call(self.on_game)),
            pystray.MenuItem("Sair do modo jogo", lambda: self._call(self.on_game_off)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: self._call(self.on_quit)),
        )
        self.icon = pystray.Icon("winh-ditado", _image(), "Winh Ditado — Win+H para ditar", menu)
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()
        return True

    def _call(self, callback) -> None:
        if callback is None:
            return
        threading.Thread(target=callback, daemon=True).start()

    def stop(self) -> None:
        try:
            if self.icon is not None:
                self.icon.stop()
        except Exception:
            pass





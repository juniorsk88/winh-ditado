"""Ponto de entrada do Winh Ditado."""

from __future__ import annotations

import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

from . import config, ui
from .app import App
from .engine import WhisperEngine
from . import platform_bind as platform

VERSION = "1.0.0"


def setup_logging(verbose: bool = False) -> logging.Logger:
    log = logging.getLogger("winh")
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not log.handlers:
        handler = RotatingFileHandler(config.logs_dir() / "winh.log", maxBytes=512 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(handler)
        if verbose:
            stream = logging.StreamHandler(sys.stdout)
            stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            log.addHandler(stream)
    return log


def model_present(cfg: dict) -> bool:
    preset = config.preset(cfg)
    folder = config.models_dir() / preset["model"].replace("/", "_")
    return folder.is_dir() and any(folder.glob("*.bin"))


def ask_again(message: str) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.title("Winh Ditado")
    root.geometry("460x150")
    root.resizable(False, False)
    tk.Label(root, text=message, wraplength=400, justify="center", font=("Segoe UI", 10)).pack(pady=(28, 14))
    tk.Button(root, text="OK", width=12, relief="flat", command=root.destroy).pack()
    root.mainloop()


def main(argv: list[str]) -> int:
    cfg = config.load()
    verbose = "--verbose" in argv or "-v" in argv
    log = setup_logging(verbose)

    if "--version" in argv:
        print(VERSION)
        return 0

    for index, item in enumerate(argv):
        if item == "--mode" and index + 1 < len(argv):
            cfg["mode"] = argv[index + 1]

    if "--status" in argv:
        preset = config.preset(cfg) if cfg.get("mode") else None
        print(f"config: {config.config_path()}")
        print(f"modo: {cfg.get('mode') or '(não escolhido)'}")
        print(f"modelo: {preset['model'] if preset else '-'} ({'baixado' if model_present(cfg) else 'ausente'})")
        print(f"modelos: {config.models_dir()}")
        print(f"logs: {config.logs_dir()}")
        return 0

    if "--transcribe-file" in argv:
        index = argv.index("--transcribe-file")
        path = argv[index + 1] if index + 1 < len(argv) else ""
        if not cfg.get("mode"):
            cfg["mode"] = "cpu"
        engine = WhisperEngine(cfg, log)
        if not engine.prepare(lambda message, progress: print(message, flush=True)):
            print(f"erro: {engine.error}", file=sys.stderr)
            return 2
        import wave

        with wave.open(path, "rb") as handle:
            pcm = handle.readframes(handle.getnframes())
            rate = handle.getframerate()
        started = time.time()
        text = engine.transcribe(pcm, rate)
        print(f"[{time.time() - started:.2f}s] {text}")
        return 0

    if not cfg.get("mode") or "--setup" in argv:
        chosen: dict[str, str] = {}
        ui.ask_mode(lambda mode: chosen.setdefault("mode", mode))
        if not chosen.get("mode"):
            return 0
        cfg["mode"] = chosen["mode"]
        config.save(cfg)
        log.info("modo escolhido: %s", cfg["mode"])

    if "--settings" in argv:
        from .settings_ui import open_settings

        open_settings()
        return 0

    if not platform.single_instance():
        from .settings_ui import open_settings

        open_settings()
        return 0

    engine = WhisperEngine(cfg, log)
    if not model_present(cfg):
        preset = config.preset(cfg)
        result: dict[str, bool] = {}

        def worker(status):
            result["ok"] = engine.prepare(lambda message, *_rest: status(message))
            return result["ok"]

        ui.progress_window(
            f"Preparando o modo {preset['label']}.\nO modelo será baixado uma única vez.",
            worker,
            lambda ok: result.setdefault("done", ok),
        )
        if not result.get("ok"):
            ask_again(f"Não consegui preparar o modelo.\n\n{engine.error or ''}")
            return 2

    app = App(cfg, log, engine=engine)
    if not app.start():
        ask_again(f"Não consegui registrar o atalho {cfg.get('hotkey')}.\n\n{app.hotkey.error}")
        return 3

    try:
        if getattr(sys, "frozen", False):
            platform.install_autostart(sys.executable, "")
    except Exception:
        log.warning("não consegui instalar o autostart", exc_info=True)

    log.info("Winh Ditado %s no ar (modo %s)", VERSION, cfg.get("mode"))
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



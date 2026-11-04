"""Controle do ditado: uma sessao, seus estados e o atalho global."""

from __future__ import annotations

import logging
import threading
import time

from . import audio, config, ui
from .engine import WhisperEngine
from . import platform_bind as platform


class App:
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    WORKING = "working"

    def __init__(self, cfg: dict, log: logging.Logger, engine=None) -> None:
        self.cfg = cfg
        self.log = log
        self.state = self.IDLE
        self.lock = threading.Lock()
        self.action = threading.Lock()
        self.engine = engine or WhisperEngine(cfg, log)
        self.capture: audio.Capture | None = None
        self.indicator = (
            ui.Indicator(
                on_pause=self._wrap(self.pause),
                on_resume=self._wrap(self.resume),
                on_stop=self._wrap(self.finish),
                level=lambda: getattr(self.capture, "level", 0.0) if self.capture else 0.0,
            )
            if cfg.get("indicator", True)
            else ui.NullIndicator()
        )
        self.tray = None
        self.hotkey = platform.Hotkey(cfg.get("hotkey") or "win+h", self._wrap(self.toggle), log)

    # -- utilidades --------------------------------------------------------
    def _wrap(self, action):
        """Executa a acao numa thread, serializando com o lock de acao."""

        def run() -> None:
            if not self.action.acquire(timeout=20):
                self.log.info("ação ignorada: outra em andamento")
                return
            try:
                action()
            except Exception as failure:
                self.log.exception("erro em %s: %s", getattr(action, "__name__", action), failure)
            finally:
                self.action.release()

        def spawn() -> None:
            threading.Thread(target=run, daemon=True).start()

        return spawn

    # -- ciclo -------------------------------------------------------------
    def start(self) -> bool:
        if not self.hotkey.start():
            self.log.error("atalho indisponível: %s", self.hotkey.error)
            return False
        self.log.info("ditado pronto: %s liga/desliga · modo %s", self.cfg.get("hotkey"), self.engine.describe())
        threading.Thread(target=self._warm, daemon=True).start()
        threading.Thread(target=self._watch_config, daemon=True).start()
        try:
            from .tray import Tray

            self.tray = Tray(
                on_settings=self._open_settings,
                on_toggle=self._wrap(self.toggle),
                on_quit=self._quit,
            )
            if not self.tray.start():
                self.log.warning("ícone da bandeja indisponível")
        except Exception:
            self.log.warning("não consegui criar o ícone da bandeja", exc_info=True)
        return True

    def _open_settings(self) -> None:
        """Abre a janela de configurações num processo próprio (Tk separado)."""
        import subprocess
        import sys

        try:
            subprocess.Popen([sys.executable, "--settings"])
        except Exception:
            self.log.exception("não consegui abrir as configurações")

    def _quit(self) -> None:
        self.log.info("saindo pelo menu da bandeja")
        try:
            self.stop()
        finally:
            import os

            os._exit(0)

    def _watch_config(self) -> None:
        """Recarrega a config quando a janela de configurações salva."""
        path = config.config_path()
        try:
            last = path.stat().st_mtime
        except Exception:
            last = 0.0
        while True:
            time.sleep(2.0)
            try:
                mtime = path.stat().st_mtime
            except Exception:
                continue
            if mtime == last:
                continue
            last = mtime
            try:
                new = config.load()
            except Exception:
                continue
            previous = (self.cfg.get("mode"), self.cfg.get("model"), self.cfg.get("compute_type"))
            current = (new.get("mode"), new.get("model"), new.get("compute_type"))
            self.cfg.clear()
            self.cfg.update(new)
            if current != previous:
                self.engine = WhisperEngine(self.cfg, self.log)
                self.log.info("configuração mudou; carregando %s", self.engine.describe())
                if self.state == self.IDLE:
                    threading.Thread(target=self._warm, daemon=True).start()
            else:
                self.log.info("configuração recarregada")

    def _warm(self) -> None:
        if not self.engine.prepare():
            self.log.error("modelo não carregou: %s", self.engine.error)

    def stop(self) -> None:
        self.hotkey.stop()
        self.indicator.stop()

    # -- acoes -------------------------------------------------------------
    def toggle(self) -> None:
        with self.lock:
            state = self.state
        self.log.info("atalho recebido (estado=%s)", state)
        if state == self.IDLE:
            self.begin()
        elif state == self.RECORDING:
            self.finish()
        elif state == self.PAUSED:
            self.resume()

    def begin(self) -> None:
        if not self.engine.ready:
            self.indicator.working()
            if not self.engine.prepare():
                self.indicator.hide()
                self.log.error("modelo indisponível: %s", self.engine.error)
                return
        self.capture = audio.Capture(self.cfg, self.log, on_text=self._on_segment)
        try:
            platform.beep("start")
            self.capture.start()
        except Exception as failure:
            self.log.exception("não consegui abrir o microfone: %s", failure)
            self.capture = None
            self.indicator.hide()
            return
        with self.lock:
            self.state = self.RECORDING
        self.indicator.recording(0.0)
        threading.Thread(target=self._watch, daemon=True).start()

    def _on_segment(self, raw: bytes, rate: int) -> str:
        """Chamado pela captura a cada trecho; devolve o texto reconhecido."""
        try:
            text = self.engine.transcribe(raw, rate)
        except Exception as failure:
            self.log.exception("falha ao transcrever: %s", failure)
            return ""
        if not text:
            return ""
        pedaco = text.strip()
        if pedaco and not pedaco.endswith((" ", "\n")):
            pedaco += " "
        self.log.info("trecho %d -> %r (em %s)", getattr(self.capture, "segment_count", 0) + 1, pedaco[:90], platform.foreground_title())
        platform.type_text(pedaco, int(self.cfg.get("type_delay_ms") or 10))
        return pedaco

    def _watch(self) -> None:
        limit = float(self.cfg.get("max_seconds") or 180)
        started = time.time()
        while True:
            time.sleep(0.5)
            with self.lock:
                if self.state != self.RECORDING:
                    return
            elapsed = time.time() - started
            self.indicator.recording(elapsed)
            if self.capture is not None and self.capture.auto_stopped:
                self.log.info("encerrado por silêncio")
                self._wrap(self.finish)()
                return
            if elapsed >= limit:
                self.log.info("limite de %.0fs atingido", limit)
                self._wrap(self.finish)()
                return

    def _close_capture(self) -> None:
        capture, self.capture = self.capture, None
        if capture is not None:
            try:
                capture.stop()
            except Exception as failure:
                self.log.warning("erro ao fechar o microfone: %s", failure)

    def pause(self) -> None:
        with self.lock:
            if self.state != self.RECORDING:
                return
            self.state = self.PAUSED
        self._close_capture()
        self.indicator.paused()
        self.log.info("ditado pausado")

    def resume(self) -> None:
        with self.lock:
            if self.state != self.PAUSED:
                return
        self.state = self.IDLE
        self.begin()

    def finish(self) -> None:
        with self.lock:
            state = self.state
            if state not in (self.RECORDING, self.PAUSED):
                return
            self.state = self.WORKING
        if state == self.PAUSED:
            self.indicator.hide()
            with self.lock:
                self.state = self.IDLE
            self.log.info("ditado encerrado enquanto pausado")
            return
        self.indicator.working()
        self._close_capture()
        self.indicator.hide()
        with self.lock:
            self.state = self.IDLE
        self.log.info("ditado encerrado")



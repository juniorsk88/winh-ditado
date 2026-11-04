"""Microfone e segmentacao por pausa (ditado continuo)."""

from __future__ import annotations

import queue
import threading
import time

import numpy as np
import sounddevice as sd

FRAME_MS = 30
NOISE_WINDOW = 100


class Capture:
    """Abre o microfone e entrega trechos de fala prontos para transcrever."""

    def __init__(self, cfg: dict, log, on_text) -> None:
        self.cfg = cfg
        self.log = log
        self.on_text = on_text
        self.sample_rate = int(cfg.get("sample_rate") or 16000)
        self.frame_samples = max(1, int(self.sample_rate * FRAME_MS / 1000))
        self.silence_cut_ms = int(cfg.get("segment_silence_ms") or 500)
        self.min_speech_ms = int(cfg.get("segment_min_ms") or 300)
        self.max_segment_ms = int(cfg.get("segment_max_ms") or 8000)
        self.auto_stop_silence = float(cfg.get("auto_stop_silence_seconds") or 20)
        self.fixed_threshold = float(cfg.get("vad_threshold") or 0)

        self.queue: queue.Queue[bytes] = queue.Queue()
        self.stop_event = threading.Event()
        self.auto_stopped = False
        self.segment_count = 0
        self.level = 0.0
        self.started = False
        self.stream = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    # -- ciclo de vida ----------------------------------------------------
    def start(self) -> None:
        device = self.cfg.get("device")
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            device=device,
            callback=self._callback,
        )
        self.stream.start()
        self.started = True
        self._thread.start()
        self.log.info("microfone aberto (%s, %s Hz)", device or "padrão", self.sample_rate)

    def _callback(self, indata, frames, time_info, status):  # noqa: ANN001
        try:
            self.queue.put_nowait(indata.copy().tobytes())
        except Exception:
            pass

    def stop(self) -> None:
        self.stop_event.set()
        try:
            self._thread.join(20.0)
        except Exception:
            pass
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self.started = False

    # -- processamento ----------------------------------------------------
    def _run(self) -> None:
        pending = b""
        segment = bytearray()
        silence_ms = 0.0
        speech_ms = 0.0
        in_segment = False
        last_voice = time.time()
        noise: list[float] = []
        frame_bytes = self.frame_samples * 2

        def finalize(trim_tail_ms: float = 0.0) -> None:
            nonlocal segment, silence_ms, speech_ms, in_segment
            if not segment:
                in_segment = False
                return
            raw = bytes(segment)
            if trim_tail_ms > 0:
                cut = int(self.sample_rate * trim_tail_ms / 1000) * 2
                raw = raw[: max(0, len(raw) - cut)]
            segment = bytearray()
            duration = len(raw) / 2 / self.sample_rate
            spoken = max(0.0, duration - silence_ms / 1000)
            in_segment = False
            silence_ms = 0.0
            speech_ms = 0.0
            if spoken * 1000 < self.min_speech_ms or duration <= 0.05:
                return
            try:
                text = self.on_text(raw, self.sample_rate)
            except Exception as failure:
                self.log.warning("falha ao transcrever trecho: %s", failure)
                return
            if text:
                self.segment_count += 1

        while True:
            stopping = self.stop_event.is_set()
            try:
                block = self.queue.get(timeout=0.2)
            except queue.Empty:
                block = b""
            if block:
                pending += block
            while len(pending) >= frame_bytes:
                frame = pending[:frame_bytes]
                pending = pending[frame_bytes:]
                samples = np.frombuffer(frame, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                self.level = min(1.0, self.level * 0.55 + min(1.0, rms / 5000.0) * 0.45)
                if self.fixed_threshold > 0:
                    threshold = self.fixed_threshold
                elif len(noise) < 12:
                    noise.append(rms)
                    threshold = 400.0
                else:
                    threshold = max(280.0, float(np.percentile(noise, 20)) * 2.2)

                if rms > threshold:
                    if not in_segment:
                        in_segment = True
                        segment = bytearray()
                        silence_ms = 0.0
                        speech_ms = 0.0
                    last_voice = time.time()
                    silence_ms = 0.0
                    speech_ms += FRAME_MS
                    segment.extend(frame)
                elif in_segment:
                    silence_ms += FRAME_MS
                    segment.extend(frame)
                else:
                    noise.append(rms)
                    if len(noise) > NOISE_WINDOW:
                        del noise[0]

                if in_segment and silence_ms >= self.silence_cut_ms:
                    finalize(trim_tail_ms=silence_ms - FRAME_MS)
                elif in_segment and speech_ms >= self.max_segment_ms:
                    finalize(trim_tail_ms=silence_ms)
                    in_segment = True
            if stopping:
                break
            if not in_segment and (time.time() - last_voice) >= self.auto_stop_silence:
                self.auto_stopped = True
                self.log.info("silêncio de %.0fs: encerrando o ditado", self.auto_stop_silence)
                break

        if in_segment:
            finalize(trim_tail_ms=silence_ms)

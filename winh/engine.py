"""Motor de reconhecimento: faster-whisper rodando dentro do proprio programa.

Nada de servico separado: o modelo carrega neste processo e cada trecho de fala
vai direto para a GPU (ou para a CPU, no modo leve).
"""

from __future__ import annotations

import ctypes
import glob
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

from . import config


def _prepare_cuda_dirs() -> list[str]:
    """Deixa as DLLs de CUDA/cuDNN visiveis para o ctranslate2 (Windows)."""
    if not config.is_windows():
        return []
    candidates: list[str] = []
    extra = os.environ.get("WINH_CUDA_DIR")
    if extra:
        candidates.append(extra)
        candidates.extend(sorted(glob.glob(os.path.join(extra, "*", "bin"))))
    local = config.cuda_dir()
    if local.is_dir():
        candidates.append(str(local))
        candidates.extend(sorted(glob.glob(str(local / "**" / "bin"), recursive=True)))
    # pacote que o instalador de GPU baixa (cublas/cudnn do pip) e a propria venv
    for base in (config.app_root(), Path(sys.executable).parent):
        candidates.extend(sorted(glob.glob(str(base / "nvidia" / "*" / "bin"))))
        candidates.extend(sorted(glob.glob(str(base / "cuda" / "*" / "bin"))))
    candidates.extend(sorted(glob.glob(str(config.data_dir() / "nvidia" / "*" / "bin"))))
    added = []
    for path in candidates:
        if not os.path.isdir(path):
            continue
        try:
            os.add_dll_directory(path)
            added.append(path)
        except Exception:
            pass
        os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
    return added


class WhisperEngine:
    def __init__(self, cfg: dict, log) -> None:
        self.cfg = cfg
        self.log = log
        self.model = None
        self.lock = threading.Lock()
        self._loading = False
        self._error: str | None = None

    # -- estado -----------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def error(self) -> str | None:
        return self._error

    def describe(self) -> str:
        preset = config.preset(self.cfg)
        return f"{preset['model']} · {preset['device']} · {preset['compute_type']}"

    # -- preparacao -------------------------------------------------------
    def prepare(self, on_progress=None) -> bool:
        """Baixa (se preciso) e carrega o modelo. Seguro para chamar de thread."""
        with self.lock:
            if self.model is not None:
                return True
            if self._loading:
                return False
            self._loading = True
        try:
            self._error = None
            preset = config.preset(self.cfg)
            target = self._download(preset["model"], on_progress)
            if on_progress:
                on_progress("Carregando o modelo na memória…", -1)
            from faster_whisper import WhisperModel

            if preset["device"] == "cuda":
                added = _prepare_cuda_dirs()
                self.log.info("DLLs de CUDA em: %s", added or "nenhuma pasta encontrada")
            started = time.time()
            self.model = WhisperModel(
                target,
                device=preset["device"],
                compute_type=preset["compute_type"],
                download_root=str(config.models_dir()),
                local_files_only=True,
            )
            self.log.info("modelo %s carregado em %.1fs (%s)", preset["model"], time.time() - started, preset["device"])
            return True
        except Exception as failure:
            self._error = _explain(failure)
            self.log.exception("falha ao preparar o modelo: %s", failure)
            return False
        finally:
            with self.lock:
                self._loading = False

    def _download(self, model_name: str, on_progress) -> str:
        """Garante o modelo no disco; devolve a pasta pronta para carregar."""
        from faster_whisper.utils import download_model

        target = config.models_dir() / model_name.replace("/", "_")
        if (target / "model.bin").exists() or any(target.glob("*.bin")):
            return str(target)
        if on_progress:
            on_progress(f"Baixando o modelo {model_name} na primeira vez…", -1)
        target.mkdir(parents=True, exist_ok=True)
        return download_model(model_name, output_dir=str(target), local_files_only=False)

    # -- uso --------------------------------------------------------------
    def transcribe(self, pcm: bytes, sample_rate: int, language: str | None = None) -> str:
        if self.model is None:
            raise RuntimeError("modelo ainda não carregado")
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self.model.transcribe(
            audio,
            language=(language or self.cfg.get("language") or "pt"),
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


def _explain(failure: Exception) -> str:
    text = str(failure)
    if "cublas" in text.lower() or "cudnn" in text.lower() or "cuda" in text.lower():
        return (
            "O modo GPU precisa das bibliotecas de CUDA, que não estão nesta máquina.\n"
            "Rode o instalador de novo e escolha “Instalar suporte a GPU”, ou use o modo CPU."
        )
    return text

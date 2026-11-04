"""Configuracao e caminhos do Winh Ditado (Windows e Linux)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "WinhDitado"

PRESETS = {
    # O modo GPU e' o mesmo que ja roda no PC do Roberto: large-v3-turbo em
    # float16 na placa, o melhor reconhecimento em portugues que temos.
    "gpu": {
        "device": "cuda",
        "compute_type": "float16",
        "model": "large-v3-turbo",
        "label": "GPU (NVIDIA, máxima qualidade)",
    },
    # No processador o gargalo e' a conta: 'small' em int8 ainda transcreve
    # rapido e cabe em qualquer PC.
    "cpu": {
        "device": "cpu",
        "compute_type": "int8",
        "model": "small",
        "label": "CPU (funciona em qualquer PC)",
    },
}

DEFAULTS = {
    "mode": "",  # "gpu" ou "cpu", escolhido na primeira execucao
    "hotkey": "win+h",
    "language": "pt",
    "device": None,  # microfone; None = padrao do sistema
    "sample_rate": 16000,
    "streaming": True,
    "auto_stop_silence_seconds": 20,
    "segment_silence_ms": 500,
    "segment_min_ms": 300,
    "segment_max_ms": 8000,
    "vad_threshold": 0,
    "beeps": True,
    "insert": "type",
    "type_delay_ms": 10,
    "indicator": True,
    "max_seconds": 180,
}


def is_windows() -> bool:
    return sys.platform.startswith("win")


def data_dir() -> Path:
    """Onde ficam config, modelos e logs (por usuario)."""
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def models_dir() -> Path:
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cuda_dir() -> Path:
    return data_dir() / "cuda"


def load() -> dict:
    cfg = dict(DEFAULTS)
    path = config_path()
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save(cfg: dict) -> None:
    config_path().write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def preset(cfg: dict) -> dict:
    """Modo (gpu/cpu) + eventuais escolhas explícitas de modelo e precisão."""
    base = dict(PRESETS.get(str(cfg.get("mode") or "cpu").lower(), PRESETS["cpu"]))
    if cfg.get("model"):
        base["model"] = cfg["model"]
    if cfg.get("compute_type"):
        base["compute_type"] = cfg["compute_type"]
    if cfg.get("model"):
        base["label"] = f"{base['device'].upper()} · {cfg['model']}"
    return base


def app_root() -> Path:
    """Pasta do programa (funciona tambem dentro do executavel)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent

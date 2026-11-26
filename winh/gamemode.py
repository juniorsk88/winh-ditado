"""Modo jogo: fecha os modelos abertos para liberar memoria e VRAM."""

from __future__ import annotations

import subprocess

ROOT = r"C:\Users\junio\.dsh\voice-stt"
LLAMA = ROOT + r"\llm\llama-server.exe"
MODEL = ROOT + r"\llm\qwen2.5-3b-instruct-q4_k_m.gguf"
PYTHONW = ROOT + r"\.venv\Scripts\pythonw.exe"
SERVER = ROOT + r"\server.py"


def _run(script: str) -> None:
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script],
        creationflags=0x08000000,
        check=False,
    )


def enter() -> None:
    """Mata o llama-server e o servico do Whisper."""
    _run(
        "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force; "
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -like '*voice-stt*server.py*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )


def leave() -> None:
    """Sobe de novo o llama-server e o servico do Whisper."""
    start = (
        f"if (-not (Get-Process llama-server -ErrorAction SilentlyContinue)) {{ "
        f"Start-Process -FilePath '{LLAMA}' -ArgumentList @('-m','{MODEL}','-ngl','99','-c','4096','-t','8','--port','8180','--host','127.0.0.1') "
        f"-WorkingDirectory '{ROOT}\\llm' -WindowStyle Hidden }}; "
        f"Start-Sleep -Seconds 4; "
        f"if (-not (Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '*voice-stt*' }})) {{ "
        f"Start-Process -FilePath '{PYTHONW}' -ArgumentList '{SERVER}' -WorkingDirectory '{ROOT}' -WindowStyle Hidden }}"
    )
    _run(start)


def models_running() -> list[str]:
    """Nomes dos modelos que estao no ar agora."""
    try:
        output = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq llama-server.exe", "/NH"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        ).stdout
        return ["llama-server"] if "llama-server" in output else []
    except Exception:
        return []

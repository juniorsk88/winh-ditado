"""Escolhe a implementacao de plataforma (Windows ou Linux)."""

from __future__ import annotations

import sys

if sys.platform.startswith("win"):
    from .platform_win import (  # noqa: F401
        Hotkey,
        beep,
        foreground_title,
        install_autostart,
        instance_exists,
        remove_autostart,
        single_instance,
        type_text,
    )
else:
    from .platform_linux import (  # noqa: F401
        Hotkey,
        available,
        beep,
        foreground_title,
        install_autostart,
        remove_autostart,
        single_instance,
        type_text,
    )

    def instance_exists() -> bool:  # pragma: no cover - Linux
        return False

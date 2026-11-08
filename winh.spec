# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para o Winh Ditado (Windows e Linux)."""

import os
import sys

from PyInstaller.utils.hooks import collect_all

ICON = "packaging/winh-ditado.ico" if (sys.platform == "win32" and os.path.exists("packaging/winh-ditado.ico")) else None

datas, binaries, hiddenimports = [], [], []
for package in (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "onnxruntime",
    "huggingface_hub",
    "sounddevice",
    "av",
):
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
    except Exception:
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    ["run_winh.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "torch", "pandas", "IPython", "pytest", "sympy"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WinhDitado",
    icon=ICON,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    onefile=True,
)


"""Configuracoes do ditado: segue o tema do Windows (claro ou escuro)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import config

MODELS = [
    ("tiny", "tiny — 39 MB · o mais rápido, qualidade baixa"),
    ("base", "base — 74 MB · rápido, qualidade razoável"),
    ("small", "small — 244 MB · equilíbrio para CPU"),
    ("medium", "medium — 769 MB · boa qualidade, CPU pesada"),
    ("large-v3", "large-v3 — 1,5 GB · máxima qualidade (GPU)"),
    ("large-v3-turbo", "large-v3-turbo — 1,5 GB · quase large-v3 e bem mais rápido (GPU)"),
    ("distil-large-v3", "distil-large-v3 — 756 MB · rápido e bom em inglês"),
]

DEVICES = [("cuda", "GPU — placa NVIDIA"), ("cpu", "CPU — processador")]

COMPUTE = [
    ("float16", "float16 — GPU, padrão"),
    ("int8_float16", "int8_float16 — GPU com menos memória"),
    ("int8", "int8 — CPU, padrão"),
    ("float32", "float32 — CPU, mais lento e preciso"),
]

LANGUAGES = [("pt", "Português"), ("en", "Inglês"), ("es", "Espanhol"), ("auto", "Detectar")]


def is_dark() -> bool:
    """Le a preferencia de tema do Windows (AppsUseLightTheme)."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except Exception:
        return False


def palette() -> dict:
    dark = is_dark()
    return {
        "dark": dark,
        "bg": "#1F1F1F" if dark else "#F3F4F6",
        "card": "#2B2B2B" if dark else "#FFFFFF",
        "fg": "#F5F5F5" if dark else "#1A1A1A",
        "muted": "#A0A0A0" if dark else "#5F6368",
        "border": "#3C3C3C" if dark else "#E0E0E0",
        "accent": "#B3261E",
        "action": "#1F4E79",
    }


def open_settings(on_saved=None) -> None:
    cfg = config.load()
    color = palette()

    root = tk.Tk()
    root.title("Winh Ditado — Configurações")
    root.geometry("640x650")
    root.resizable(False, False)
    root.configure(bg=color["bg"])

    header = tk.Frame(root, bg=color["accent"], height=74)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(header, text="Winh Ditado", font=("Segoe UI Semibold", 16), bg=color["accent"], fg="#FFFFFF").place(x=22, y=14)
    tk.Label(
        header,
        text="Ditado com Whisper local · Win+H",
        font=("Segoe UI", 9),
        bg=color["accent"],
        fg="#FFE3E0",
    ).place(x=24, y=44)

    body = tk.Frame(root, bg=color["bg"])
    body.pack(fill="both", expand=True, padx=18, pady=14)

    card = tk.Frame(body, bg=color["card"], highlightthickness=1, highlightbackground=color["border"])
    card.pack(fill="x")

    def add_row(parent, label: str, hint: str = "") -> ttk.Combobox:
        line = tk.Frame(parent, bg=color["card"])
        line.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(
            line, text=label, width=14, anchor="w", bg=color["card"], fg=color["fg"], font=("Segoe UI", 9)
        ).pack(side="left")
        box = ttk.Combobox(line, state="readonly", width=44, font=("Segoe UI", 9))
        box.pack(side="left", fill="x", expand=True)
        if hint:
            tk.Label(
                parent, text=hint, bg=color["card"], fg=color["muted"], font=("Segoe UI", 8), anchor="w"
            ).pack(fill="x", padx=(140, 16), pady=(0, 2))
        return box

    preset = config.preset(cfg)

    device_box = add_row(card, "Processamento")
    device_box["values"] = [label for _, label in DEVICES]
    device_box.set(dict(DEVICES).get(preset["device"], DEVICES[1][1]))

    model_box = add_row(card, "Modelo", "Modelos maiores são mais precisos e mais lentos.")
    model_box["values"] = [label for _, label in MODELS]
    model_box.set(next((label for name, label in MODELS if name == preset["model"]), MODELS[2][1]))

    compute_box = add_row(card, "Precisão")
    compute_box["values"] = [label for _, label in COMPUTE]
    compute_box.set(next((label for name, label in COMPUTE if name == preset["compute_type"]), COMPUTE[2][1]))

    language_box = add_row(card, "Idioma")
    language_box["values"] = [label for _, label in LANGUAGES]
    language_box.set(dict(LANGUAGES).get(cfg.get("language") or "pt", "Português"))

    microphones = ["Padrão do sistema"]
    try:
        import sounddevice as sd

        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                microphones.append(f"{index}: {device['name']}")
    except Exception:
        pass
    mic_box = add_row(card, "Microfone")
    mic_box["values"] = microphones
    wanted = cfg.get("device")
    mic_box.set(
        microphones[0]
        if wanted is None
        else next((item for item in microphones if item.startswith(f"{wanted}:")), microphones[0])
    )

    insert_box = add_row(card, "Inserir texto")
    insert_box["values"] = ["Digitar (recomendado)", "Colar da área de transferência"]
    insert_box.set("Colar da área de transferência" if cfg.get("insert") == "paste" else "Digitar (recomendado)")

    hotkey_box = add_row(card, "Atalho")
    hotkey_box["values"] = [cfg.get("hotkey") or "win+h"]
    hotkey_box.set(cfg.get("hotkey") or "win+h")

    tk.Frame(card, bg=color["card"], height=10).pack(fill="x")

    options_card = tk.Frame(body, bg=color["card"], highlightthickness=1, highlightbackground=color["border"])
    options_card.pack(fill="x", pady=(12, 0))
    tk.Label(
        options_card, text="Comportamento", bg=color["card"], fg=color["muted"], font=("Segoe UI", 8), anchor="w"
    ).pack(fill="x", padx=16, pady=(10, 0))

    beeps = tk.BooleanVar(value=bool(cfg.get("beeps", True)))
    indicator = tk.BooleanVar(value=bool(cfg.get("indicator", True)))
    streaming = tk.BooleanVar(value=bool(cfg.get("streaming", True)))
    for text, variable in (
        ("Som ao iniciar e terminar", beeps),
        ("Mostrar a pílula na tela", indicator),
        ("Texto aparecendo enquanto falo", streaming),
    ):
        tk.Checkbutton(
            options_card,
            text=text,
            variable=variable,
            bg=color["card"],
            fg=color["fg"],
            activebackground=color["card"],
            activeforeground=color["fg"],
            selectcolor=color["card"],
            anchor="w",
            font=("Segoe UI", 9),
            highlightthickness=0,
        ).pack(fill="x", padx=12, pady=1)

    status = tk.Label(body, text="", bg=color["bg"], fg=color["action"], font=("Segoe UI", 9))
    status.pack(pady=(10, 0))

    buttons = tk.Frame(body, bg=color["bg"])
    buttons.pack(pady=(6, 0))

    def save() -> None:
        device_name = dict((label, name) for name, label in DEVICES)[device_box.get()]
        model_name = dict((label, name) for name, label in MODELS)[model_box.get()]
        compute_name = dict((label, name) for name, label in COMPUTE)[compute_box.get()]
        cfg.update(
            {
                "mode": "gpu" if device_name == "cuda" else "cpu",
                "model": model_name,
                "compute_type": compute_name,
                "language": dict((label, name) for name, label in LANGUAGES)[language_box.get()],
                "insert": "paste" if insert_box.get().startswith("Colar") else "type",
                "beeps": bool(beeps.get()),
                "indicator": bool(indicator.get()),
                "streaming": bool(streaming.get()),
                "device": None if mic_box.get().startswith("Padrão") else int(mic_box.get().split(":")[0]),
            }
        )
        config.save(cfg)
        status.configure(text="Salvo — aplica em alguns segundos.")
        if on_saved:
            on_saved(cfg)

    tk.Button(
        buttons,
        text="Salvar",
        width=14,
        bg=color["action"],
        fg="white",
        activebackground=color["action"],
        activeforeground="white",
        relief="flat",
        bd=0,
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
        command=save,
    ).pack(side="left", padx=6)
    tk.Button(
        buttons,
        text="Fechar",
        width=14,
        bg=color["card"],
        fg=color["fg"],
        relief="flat",
        bd=0,
        font=("Segoe UI", 9),
        cursor="hand2",
        command=root.destroy,
    ).pack(side="left", padx=6)

    root.mainloop()

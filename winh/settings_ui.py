"""Janela de configuracoes: modo, modelo, idioma, microfone e comportamento."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import config

MODELS = [
    ("tiny", "tiny — 39 MB, o mais rápido, qualidade baixa"),
    ("base", "base — 74 MB, rápido, qualidade razoável"),
    ("small", "small — 244 MB, equilíbrio para CPU"),
    ("medium", "medium — 769 MB, boa qualidade, CPU pesada"),
    ("large-v3", "large-v3 — 1,5 GB, máxima qualidade (GPU)"),
    ("large-v3-turbo", "large-v3-turbo — 1,5 GB, quase large-v3 e bem mais rápido (GPU)"),
    ("distil-large-v3", "distil-large-v3 — 756 MB, rápido e bom em inglês"),
]

DEVICES = [
    ("cuda", "GPU (placa NVIDIA)"),
    ("cpu", "CPU (processador)"),
]

COMPUTE = [
    ("float16", "float16 (GPU, padrão)"),
    ("int8_float16", "int8_float16 (GPU com menos memória)"),
    ("int8", "int8 (CPU, padrão)"),
    ("float32", "float32 (CPU, mais lento e mais preciso)"),
]


def open_settings(on_saved=None) -> None:
    cfg = config.load()

    root = tk.Tk()
    root.title("Winh Ditado — Configurações")
    root.geometry("560x620")
    root.resizable(False, False)
    root.configure(bg="#F7F7F7")

    tk.Label(root, text="Configurações do ditado", font=("Segoe UI", 13, "bold"), bg="#F7F7F7").pack(pady=(18, 12))

    form = tk.Frame(root, bg="#F7F7F7")
    form.pack(fill="x", padx=28)

    def row(label: str) -> tk.Widget:
        holder = tk.Frame(form, bg="#F7F7F7")
        holder.pack(fill="x", pady=6)
        tk.Label(holder, text=label, width=16, anchor="w", bg="#F7F7F7", font=("Segoe UI", 9)).pack(side="left")
        widget = ttk.Combobox(holder, state="readonly", width=42)
        widget.pack(side="left", fill="x", expand=True)
        return widget

    device_box = row("Processamento")
    model_box = row("Modelo")
    compute_box = row("Precisão")
    language_box = row("Idioma")
    mic_box = row("Microfone")
    insert_box = row("Inserir texto")
    hotkey_entry = row("Atalho")

    device_values = [label for _, label in DEVICES]
    device_box["values"] = device_values
    device_box.set(dict(DEVICES).get(config.preset(cfg)["device"], device_values[1]))

    model_values = [label for _, label in MODELS]
    model_box["values"] = model_values
    current_model = config.preset(cfg)["model"]
    model_box.set(next((label for name, label in MODELS if name == current_model), model_values[2]))

    compute_values = [label for _, label in COMPUTE]
    compute_box["values"] = compute_values
    current_compute = config.preset(cfg)["compute_type"]
    compute_box.set(next((label for name, label in COMPUTE if name == current_compute), compute_values[2]))

    languages = [("pt", "Português"), ("en", "Inglês"), ("es", "Espanhol"), ("auto", "Detectar")]
    language_box["values"] = [label for _, label in languages]
    language_box.set(dict(languages).get(cfg.get("language") or "pt", "Português"))

    microphones = ["Padrão do sistema"]
    try:
        import sounddevice as sd

        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                microphones.append(f"{index}: {device['name']}")
    except Exception:
        pass
    mic_box["values"] = microphones
    wanted = cfg.get("device")
    mic_box.set(microphones[0] if wanted is None else next((m for m in microphones if m.startswith(f"{wanted}:")), microphones[0]))

    insert_box["values"] = ["Digitar (recomendado)", "Colar da área de transferência"]
    insert_box.set("Colar da área de transferência" if cfg.get("insert") == "paste" else "Digitar (recomendado)")

    hotkey_entry.configure(state="normal")
    hotkey_entry.insert(0, cfg.get("hotkey") or "win+h")
    hotkey_entry.configure(state="readonly")

    beeps = tk.BooleanVar(value=bool(cfg.get("beeps", True)))
    indicator = tk.BooleanVar(value=bool(cfg.get("indicator", True)))
    streaming = tk.BooleanVar(value=bool(cfg.get("streaming", True)))

    options = tk.Frame(root, bg="#F7F7F7")
    options.pack(fill="x", padx=28, pady=(10, 0))
    for text, variable in (
        ("Som ao iniciar e terminar", beeps),
        ("Mostrar a pílula na tela", indicator),
        ("Texto aparecendo enquanto falo", streaming),
    ):
        tk.Checkbutton(options, text=text, variable=variable, bg="#F7F7F7", anchor="w").pack(fill="x")

    status = tk.Label(root, text="", bg="#F7F7F7", fg="#1F4E79", font=("Segoe UI", 9))
    status.pack(pady=(10, 0))

    def save() -> None:
        device_name = dict((label, name) for name, label in DEVICES)[device_box.get()]
        model_name = dict((label, name) for name, label in MODELS)[model_box.get()]
        compute_name = dict((label, name) for name, label in COMPUTE)[compute_box.get()]
        language_name = dict((label, name) for name, label in languages)[language_box.get()]

        cfg["mode"] = "gpu" if device_name == "cuda" else "cpu"
        cfg["model"] = model_name
        cfg["compute_type"] = compute_name
        cfg["language"] = language_name
        cfg["insert"] = "paste" if insert_box.get().startswith("Colar") else "type"
        cfg["beeps"] = bool(beeps.get())
        cfg["indicator"] = bool(indicator.get())
        cfg["streaming"] = bool(streaming.get())
        mic = mic_box.get()
        cfg["device"] = None if mic.startswith("Padrão") else int(mic.split(":")[0])
        config.save(cfg)
        status.configure(text="Salvo. O ditado aplica em alguns segundos.")
        if on_saved:
            on_saved(cfg)

    buttons = tk.Frame(root, bg="#F7F7F7")
    buttons.pack(pady=(14, 0))
    tk.Button(buttons, text="Salvar", width=14, bg="#1F4E79", fg="white", relief="flat", command=save).pack(side="left", padx=6)
    tk.Button(buttons, text="Fechar", width=14, relief="flat", command=root.destroy).pack(side="left", padx=6)

    root.mainloop()

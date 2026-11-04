"""Interface: pílula do ditado e janela de primeira execucao."""

from __future__ import annotations

import ctypes
import math
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from . import config

if config.is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_LAYERED = 0x00080000
else:
    user32 = None

RECORD_BG = "#B3261E"
WORK_BG = "#1F4E79"
PAUSE_BG = "#4A4A4A"
TEXT_FG = "#FFFFFF"
BARS = 12
BAR_WIDTH = 3
BAR_GAP = 3
BAR_MIN = 3
BAR_MAX = 18


def _shade(hex_color: str, factor: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r * factor))),
        max(0, min(255, int(g * factor))),
        max(0, min(255, int(b * factor))),
    )


class Indicator:
    """Pílula flutuante com onda do microfone e botoes pausar/retomar/fechar."""

    def __init__(self, on_pause=None, on_resume=None, on_stop=None, level=None) -> None:
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_stop = on_stop
        self.level = level or (lambda: 0.0)
        self._queue: queue.Queue[tuple] = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def recording(self, seconds: float = 0.0) -> None:
        self._queue.put(("show", f"Gravando {_mmss(seconds)}", RECORD_BG, "pause"))

    def paused(self) -> None:
        self._queue.put(("show", "Pausado", PAUSE_BG, "resume"))

    def working(self) -> None:
        self._queue.put(("show", "Transcrevendo…", WORK_BG, "none"))

    def hide(self) -> None:
        self._queue.put(("hide",))

    def stop(self) -> None:
        self._queue.put(("quit",))

    def _run(self) -> None:
        state = {"visible": False, "mode": "pause", "bg": RECORD_BG, "level": 0.0}
        try:
            root = tk.Tk()
            root.withdraw()
            window = tk.Toplevel(root)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.attributes("-alpha", 0.0)
            window.configure(bg=RECORD_BG)

            frame = tk.Frame(window, bg=RECORD_BG, padx=14, pady=6)
            frame.pack()
            canvas = tk.Canvas(
                frame,
                width=BARS * (BAR_WIDTH + BAR_GAP) - BAR_GAP,
                height=BAR_MAX,
                bg=RECORD_BG,
                highlightthickness=0,
                bd=0,
            )
            canvas.pack(side="left", padx=(0, 10))
            label = tk.Label(frame, text="", font=("Segoe UI", 10, "bold"), fg=TEXT_FG, bg=RECORD_BG, bd=0)
            label.pack(side="left")

            def make_button(glyph: str, command) -> tk.Button:
                button = tk.Button(
                    frame,
                    text=glyph,
                    command=command,
                    font=("Segoe UI Symbol", 11, "bold"),
                    fg=TEXT_FG,
                    bg=RECORD_BG,
                    activeforeground=TEXT_FG,
                    activebackground=_shade(RECORD_BG, 1.45),
                    bd=0,
                    relief="flat",
                    padx=7,
                    pady=0,
                    cursor="hand2",
                    takefocus=0,
                )
                button.pack(side="right", padx=(8, 0))
                button.bind("<Enter>", lambda _e, b=button: b.configure(bg=_shade(state["bg"], 1.35)))
                button.bind("<Leave>", lambda _e, b=button: b.configure(bg=state["bg"]))
                button.bind(
                    "<ButtonPress-1>",
                    lambda _e, b=button: b.configure(bg="#FFFFFF", fg=state["bg"], relief="sunken", borderwidth=1),
                )
                button.bind(
                    "<ButtonRelease-1>",
                    lambda _e, b=button: b.configure(bg=_shade(state["bg"], 1.35), fg=TEXT_FG, relief="flat", borderwidth=0),
                )
                return button

            close_button = make_button("✕", lambda: click_close())
            pause_button = make_button("❚❚", lambda: click_pause())

            window.update_idletasks()
            _place(window)
            if user32 is not None:
                hwnd = _top_level_handle(window)
                if hwnd:
                    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    user32.SetWindowLongW(
                        hwnd,
                        GWL_EXSTYLE,
                        style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED,
                    )
            window.deiconify()
            window.update_idletasks()
            _place(window)
        except Exception:
            return

        rects = []
        for index in range(BARS):
            x = index * (BAR_WIDTH + BAR_GAP)
            rects.append(canvas.create_rectangle(x, BAR_MAX, x + BAR_WIDTH, BAR_MAX, fill=TEXT_FG, outline=""))

        def fire(callback) -> None:
            if callback:
                try:
                    callback()
                except Exception:
                    pass

        def paint(text: str, color: str, mode: str) -> None:
            state["bg"] = color
            state["mode"] = mode
            label.configure(text=text, bg=color)
            frame.configure(bg=color)
            window.configure(bg=color)
            canvas.configure(bg=color)
            for widget in (label, pause_button, close_button):
                widget.configure(bg=color, activebackground=_shade(color, 1.45))
            if mode == "resume":
                pause_button.configure(text="▶", command=lambda: click_resume())
            elif mode == "pause":
                pause_button.configure(text="❚❚", command=lambda: click_pause())
            pause_button.configure(state="normal" if mode != "none" else "disabled")
            if mode != "pause":
                for index, rect in enumerate(rects):
                    x = index * (BAR_WIDTH + BAR_GAP)
                    canvas.coords(rect, x, BAR_MAX, x + BAR_WIDTH, BAR_MAX)
            if not state["visible"]:
                window.attributes("-alpha", 1.0)
                state["visible"] = True
            _place(window)

        def click_pause() -> None:
            paint("Pausado", PAUSE_BG, "resume")
            fire(self.on_pause)

        def click_resume() -> None:
            paint("Gravando 0:00", RECORD_BG, "pause")
            fire(self.on_resume)

        def click_close() -> None:
            paint("Encerrando…", WORK_BG, "none")
            fire(self.on_stop)

        def tick() -> None:
            try:
                if state["visible"] and state["mode"] == "pause":
                    level = max(0.0, min(1.0, float(self.level() or 0.0)))
                    state["level"] = state["level"] * 0.55 + level * 0.45
                    now = time.time()
                    for index, rect in enumerate(rects):
                        osc = 0.35 + 0.65 * abs(math.sin(now * 7.5 + index * 0.85))
                        altura = max(BAR_MIN, min(BAR_MAX, BAR_MIN + (BAR_MAX - BAR_MIN) * state["level"] * osc))
                        x = index * (BAR_WIDTH + BAR_GAP)
                        canvas.coords(rect, x, BAR_MAX - altura, x + BAR_WIDTH, BAR_MAX)
            except Exception:
                pass
            try:
                root.after(45, tick)
            except Exception:
                pass

        def apply(message: tuple) -> None:
            action = message[0]
            if action == "show":
                _, text, color, mode = message
                paint(text, color, mode)
            elif action == "hide":
                if state["visible"]:
                    window.attributes("-alpha", 0.0)
                    state["visible"] = False
            elif action == "quit":
                root.quit()

        def pump() -> None:
            try:
                while True:
                    apply(self._queue.get_nowait())
            except queue.Empty:
                pass
            except Exception:
                pass
            try:
                root.after(80, pump)
            except Exception:
                pass

        pump()
        tick()
        root.mainloop()
        try:
            root.destroy()
        except Exception:
            pass


def _place(window: tk.Toplevel) -> None:
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    x = window.winfo_screenwidth() - width - 48
    y = window.winfo_screenheight() - height - 72
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.update_idletasks()


def _top_level_handle(window: tk.Misc) -> int:
    hwnd = int(window.winfo_id())
    parent = user32.GetParent(hwnd)
    return parent or hwnd


def _mmss(seconds: float) -> str:
    total = int(max(0, seconds))
    return f"{total // 60}:{total % 60:02d}"


class NullIndicator:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def recording(self, seconds: float = 0.0) -> None:
        pass

    def paused(self) -> None:
        pass

    def working(self) -> None:
        pass

    def hide(self) -> None:
        pass

    def stop(self) -> None:
        pass


# ---------------------------------------------------------------------------
# primeira execucao
# ---------------------------------------------------------------------------
def ask_mode(on_ready) -> None:
    """Janela de escolha do modo; chama on_ready(modo) ao terminar."""
    root = tk.Tk()
    root.title("Winh Ditado")
    root.geometry("520x300")
    root.resizable(False, False)
    root.configure(bg="#F7F7F7")

    title = tk.Label(root, text="Como este computador vai transcrever?", font=("Segoe UI", 13, "bold"), bg="#F7F7F7")
    title.pack(pady=(22, 4))
    subtitle = tk.Label(
        root,
        text="Você pode trocar depois rodando o programa de novo.",
        font=("Segoe UI", 9),
        fg="#555555",
        bg="#F7F7F7",
    )
    subtitle.pack(pady=(0, 16))

    def pick(mode: str) -> None:
        root.destroy()
        on_ready(mode)

    gpu = tk.Button(
        root,
        text="GPU — placa NVIDIA\nmelhor qualidade (large-v3-turbo)",
        font=("Segoe UI", 10, "bold"),
        bg="#1F4E79",
        fg="white",
        activebackground="#2A6398",
        activeforeground="white",
        relief="flat",
        height=3,
        command=lambda: pick("gpu"),
    )
    gpu.pack(fill="x", padx=40, pady=6)
    cpu = tk.Button(
        root,
        text="CPU — qualquer computador\nmais leve (small)",
        font=("Segoe UI", 10, "bold"),
        bg="#4A4A4A",
        fg="white",
        activebackground="#5C5C5C",
        activeforeground="white",
        relief="flat",
        height=3,
        command=lambda: pick("cpu"),
    )
    cpu.pack(fill="x", padx=40, pady=6)
    tk.Button(root, text="Sair", relief="flat", bg="#F7F7F7", command=lambda: pick("")).pack(pady=(8, 0))
    root.mainloop()


def progress_window(title: str, worker, on_done) -> None:
    """Janela com barra indeterminada enquanto o worker roda em thread."""
    root = tk.Tk()
    root.title("Winh Ditado")
    root.geometry("520x160")
    root.resizable(False, False)
    label = tk.Label(root, text=title, font=("Segoe UI", 10), wraplength=460, justify="center")
    label.pack(pady=(26, 14))
    bar = ttk.Progressbar(root, mode="indeterminate", length=420)
    bar.pack()
    bar.start(12)
    status = tk.Label(root, text="", font=("Segoe UI", 9), fg="#555555")
    status.pack(pady=(10, 0))

    def set_status(text: str) -> None:
        try:
            root.after(0, lambda: status.configure(text=text))
        except Exception:
            pass

    def run() -> None:
        result = worker(set_status)
        root.after(0, lambda: finish(result))

    def finish(result) -> None:
        bar.stop()
        root.destroy()
        on_done(result)

    threading.Thread(target=run, daemon=True).start()
    root.mainloop()

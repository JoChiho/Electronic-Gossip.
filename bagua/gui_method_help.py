"""GUI 起卦方式说明窗口。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from bagua.divination.registry import DIVINATION_METHODS, method_help_text
from bagua.gui_theme import FONT_UI, THEME


def show_method_help_dialog(parent: tk.Widget, *, current_method: str | None = None) -> None:
    """打开起卦方式说明（Notebook 分页 + 总览）。"""
    win = tk.Toplevel(parent)
    win.title("起卦方式说明")
    win.transient(parent)
    win.grab_set()
    win.configure(bg=THEME["bg"])

    outer = ttk.Frame(win, padding=12)
    outer.pack(fill=tk.BOTH, expand=True)

    notebook = ttk.Notebook(outer)
    notebook.pack(fill=tk.BOTH, expand=True)

    overview = _scrolled_text_frame(notebook, method_help_text())
    notebook.add(overview, text="  总览  ")
    select_index = 0

    for i, info in enumerate(DIVINATION_METHODS):
        page = _scrolled_text_frame(notebook, method_help_text(info.key))
        notebook.add(page, text=f"  {info.label}  ")
        if current_method == info.key:
            select_index = i + 1

    notebook.select(select_index)
    ttk.Button(outer, text="关闭", command=win.destroy).pack(pady=(10, 0))
    win.update_idletasks()
    w = max(480, int(win.winfo_reqwidth()))
    h = max(420, int(win.winfo_reqheight()))
    win.geometry(f"{w}x{h}")
    win.minsize(400, 360)


def _scrolled_text_frame(parent: tk.Widget, content: str) -> ttk.Frame:
    frame = ttk.Frame(parent)
    text = tk.Text(
        frame,
        wrap=tk.WORD,
        font=FONT_UI,
        bg=THEME["surface"],
        fg=THEME["text"],
        relief=tk.FLAT,
        borderwidth=0,
        padx=10,
        pady=10,
    )
    scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.insert("1.0", content)
    text.configure(state=tk.DISABLED)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    return frame
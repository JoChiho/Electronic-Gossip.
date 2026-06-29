"""GUI 偏好设置对话框。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from bagua.config import save_config
from bagua.gui_theme import FONT_UI, THEME
from bagua.true_solar import default_longitude

if TYPE_CHECKING:
    from bagua.gui_app import BaguaGuiApp


def show_settings_dialog(app: BaguaGuiApp) -> None:
    win = tk.Toplevel(app)
    win.title("偏好设置")
    win.configure(bg=THEME["bg"])
    win.geometry("460x380")
    win.resizable(False, False)
    win.transient(app)
    win.grab_set()

    frame = ttk.Frame(win, padding=16)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame,
        text="以下选项对 CLI 与 GUI 均生效（保存至 ~/.bagua/config.json）",
        style="Muted.TLabel",
        wraplength=400,
    ).pack(anchor=tk.W, pady=(0, 12))

    auto_bazi_var = tk.BooleanVar(value=app._config.auto_bazi)
    auto_copy_var = tk.BooleanVar(value=app._config.auto_copy_prompt)
    hex_text_var = tk.BooleanVar(value=app._config.include_hexagram_texts)
    true_solar_var = tk.BooleanVar(value=app._config.use_true_solar)

    ttk.Checkbutton(frame, text="自动排八字（出生时间已填且八字为空时）", variable=auto_bazi_var).pack(
        anchor=tk.W, pady=4
    )
    ttk.Checkbutton(frame, text="起卦后自动复制 AI 提示词到剪贴板", variable=auto_copy_var).pack(
        anchor=tk.W, pady=4
    )
    ttk.Checkbutton(frame, text="AI 提示词附带卦辞摘要", variable=hex_text_var).pack(
        anchor=tk.W, pady=4
    )
    ttk.Checkbutton(
        frame,
        text="时间起卦使用真太阳时（公历输入自动换算节气历算卦）",
        variable=true_solar_var,
    ).pack(anchor=tk.W, pady=4)

    lon_row = ttk.Frame(frame)
    lon_row.pack(fill=tk.X, pady=(10, 0))
    ttk.Label(lon_row, text="经度（东经°，可选）", style="Field.TLabel").pack(side=tk.LEFT)
    lon_var = tk.StringVar(
        value="" if app._config.longitude is None else f"{app._config.longitude:.2f}",
    )
    ttk.Entry(lon_row, textvariable=lon_var, width=12).pack(side=tk.LEFT, padx=(8, 0))
    preset_lon = default_longitude(app._config.timezone)
    ttk.Label(
        lon_row,
        text=f"留空则用时区默认 {preset_lon:.1f}°",
        style="Muted.TLabel",
    ).pack(side=tk.LEFT, padx=(8, 0))

    ttk.Label(
        frame,
        text="公历输入习惯不变；起卦与 AI 提示词自动展示节气历分量，便于准确解读。",
        style="Muted.TLabel",
        wraplength=400,
        font=FONT_UI,
    ).pack(anchor=tk.W, pady=(12, 0))

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill=tk.X, pady=(20, 0))

    def _parse_longitude() -> float | None:
        raw = lon_var.get().strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _save() -> None:
        lon = _parse_longitude()
        if lon_var.get().strip() and lon is None:
            messagebox.showerror("输入错误", "经度请填写数字（东经为正，如 121.47）")
            return
        app._config.auto_bazi = auto_bazi_var.get()
        app._config.auto_copy_prompt = auto_copy_var.get()
        app._config.include_hexagram_texts = hex_text_var.get()
        app._config.use_true_solar = true_solar_var.get()
        app._config.longitude = lon
        app._persist_config_from_form()
        save_config(app._config)
        app.status_var.set("偏好设置已保存")
        win.destroy()

    ttk.Button(btn_row, text="保存", style="Accent.TButton", command=_save).pack(side=tk.RIGHT)
    ttk.Button(btn_row, text="取消", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))
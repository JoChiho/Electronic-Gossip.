"""bagua Tkinter 主窗口。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Literal, cast

from bagua.clipboard import copy_to_clipboard
from bagua.config import load_config
from bagua.gui_canvas import HexagramCanvas
from bagua.gui_constants import APP_SUBTITLE, APP_TITLE, DISCLAIMER
from bagua.gui_display import format_hexagram_display
from bagua.gui_forms import GuiFormsMixin
from bagua.gui_history import open_history_window
from bagua.gui_settings import show_settings_dialog
from bagua.gui_theme import FONT_MONO, FONT_UI, THEME, apply_theme, style_text_widget
from bagua.models import DivinationRecord, DivinationResult, UserContext
from bagua.records import save_record
from bagua.service import perform_divination
from bagua.timezone import parse_datetime_input


class BaguaGuiApp(GuiFormsMixin, tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} · 易经八卦占卜")
        self.minsize(900, 760)
        self.geometry("960x820")

        self._config = load_config()
        self._last_result: DivinationResult | None = None
        self._coin_vars: list[list[tk.StringVar]] = []
        self._autosave_job: str | None = None
        self._loading_form = False

        apply_theme(self)
        self._build_widgets()
        self._load_form_from_config()
        self._bind_autosave()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = tk.Frame(parent, bg=THEME["header_to"], height=88)
        header.pack(fill=tk.X, pady=(0, 12))
        header.pack_propagate(False)

        accent = tk.Frame(header, bg=THEME["accent"], width=4)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        text_col = tk.Frame(header, bg=THEME["header_to"])
        text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 12), pady=14)

        tk.Label(
            text_col,
            text=APP_TITLE,
            bg=THEME["header_to"],
            fg=THEME["accent"],
            font=("Microsoft YaHei UI", 22, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            text_col,
            text=APP_SUBTITLE,
            bg=THEME["header_to"],
            fg=THEME["text_muted"],
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W, pady=(2, 0))
        tk.Label(
            text_col,
            text=DISCLAIMER,
            bg=THEME["header_to"],
            fg=THEME["text_muted"],
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor=tk.W, pady=(6, 0))

        right_col = tk.Frame(header, bg=THEME["header_to"])
        right_col.pack(side=tk.RIGHT, padx=16, pady=10)
        ttk.Button(right_col, text="⚙ 设置", command=self._show_settings).pack(anchor=tk.E)
        tk.Label(
            right_col,
            text="☰\n☷",
            bg=THEME["header_to"],
            fg=THEME["accent_dim"],
            font=("Segoe UI Symbol", 18),
            justify=tk.CENTER,
        ).pack(pady=(8, 0))

    def _build_widgets(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_header(outer)

        body = ttk.Frame(outer)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        right = ttk.Frame(body)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        scroll_canvas = tk.Canvas(
            left, highlightthickness=0, bg=THEME["bg"], borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scroll_frame = ttk.Frame(scroll_canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")),
        )
        scroll_canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_user_section(scroll_frame)
        self._build_method_section(scroll_frame)

        self.options_container = ttk.Frame(scroll_frame)
        self.options_container.pack(fill=tk.X, pady=(0, 4))
        self._build_coin_section(self.options_container)
        self._build_time_section(self.options_container)

        self._build_action_section(scroll_frame)

        self._build_result_section(right)
        self._build_prompt_section(right)

        self.status_var = tk.StringVar(value="就绪 · 设定将自动保存")
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self._on_method_changed()
        self._on_coin_mode_changed()

    def _build_action_section(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(frame, text="☯  起  卦", style="Accent.TButton", command=self._on_divinate).pack(
            side=tk.LEFT
        )
        ttk.Label(
            frame,
            text="修改任意选项后将自动保存",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(14, 0))

    def _build_result_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  卦象结果  ", style="Section.TLabelframe", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.hexagram_canvas = HexagramCanvas(frame, width=300, height=250)
        self.hexagram_canvas.pack(fill=tk.X, pady=(0, 10))
        self.hexagram_canvas.draw_hexagram(None)

        self.result_text = scrolledtext.ScrolledText(
            frame, height=14, wrap=tk.WORD, font=FONT_MONO,
        )
        style_text_widget(self.result_text, readonly=True)
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _build_prompt_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="  AI 解读提示词  ", style="Section.TLabelframe", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.prompt_text = scrolledtext.ScrolledText(
            frame, height=16, wrap=tk.WORD, font=FONT_UI,
        )
        style_text_widget(self.prompt_text)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="复制提示词", command=self._copy_prompt).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="保存记录", command=self._save_record).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_row, text="历史记录", style="Ghost.TButton", command=self._show_history).pack(
            side=tk.RIGHT
        )

    def _set_text_widget(self, widget: scrolledtext.ScrolledText, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        if widget is self.result_text:
            widget.configure(state=tk.DISABLED)

    def _on_divinate(self) -> None:
        try:
            ctx = self._build_context()
            method = cast(Literal["coin", "time", "random"], self.method_var.get())
            coin_tosses = None
            divination_dt = None
            coin_mode = self.coin_mode_var.get()

            if method == "coin":
                coin_tosses = self._collect_coin_tosses()
            elif method == "time":
                lunar_input = None
                if not self.use_now_var.get():
                    raw = self.time_input_var.get().strip()
                    if ctx.calendar_mode == "lunar":
                        from bagua.lunar_util import parse_lunar_datetime_input

                        if parse_lunar_datetime_input(raw) is None:
                            messagebox.showerror("输入错误", "农历时间格式无效，请使用如 2026-05-10 14:30")
                            return
                        lunar_input = raw
                    else:
                        divination_dt = parse_datetime_input(raw, ctx.tz)
                        if divination_dt is None:
                            messagebox.showerror("输入错误", "公历时间格式无效，请使用如 2026-06-24 14:30")
                            return
                if ctx.calendar_mode == "lunar" and lunar_input:
                    ctx = UserContext(
                        question=ctx.question,
                        bazi=ctx.bazi,
                        birth_datetime=ctx.birth_datetime,
                        tz=ctx.tz,
                        coin_mode=ctx.coin_mode,
                        calendar_mode=ctx.calendar_mode,
                        lunar_input=lunar_input,
                        include_hexagram_texts=ctx.include_hexagram_texts,
                        longitude=ctx.longitude,
                        use_true_solar=ctx.use_true_solar,
                    )

            result = perform_divination(
                method,
                ctx,
                coin_tosses=coin_tosses,
                divination_datetime=divination_dt,
                coin_mode=coin_mode,
                auto_bazi=self._config.auto_bazi,
            )
            self._last_result = result

            result_lines = [
                f"起卦时间：{result.divination_time}",
                f"起卦方法：{result.method_desc}",
                "",
                format_hexagram_display(result.hexagram),
            ]
            self._set_text_widget(self.result_text, "\n".join(result_lines))
            self._set_text_widget(self.prompt_text, result.prompt)
            self.hexagram_canvas.draw_hexagram(result.hexagram)

            self._persist_config_from_form()
            if self._config.auto_copy_prompt and copy_to_clipboard(result.prompt):
                self.status_var.set("起卦完成 · 提示词已复制到剪贴板")
            else:
                self.status_var.set("起卦完成")
        except Exception as exc:
            messagebox.showerror("起卦失败", str(exc))
            self.status_var.set("起卦失败")

    def _copy_prompt(self) -> None:
        text = self.prompt_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("提示", "暂无提示词可复制")
            return
        if copy_to_clipboard(text):
            self.status_var.set("已复制到剪贴板")
        else:
            messagebox.showwarning("复制失败", "无法写入剪贴板，请手动选择文本复制")

    def _save_record(self) -> None:
        if self._last_result is None:
            messagebox.showinfo("提示", "请先起卦")
            return
        ctx = self._build_context()
        record = DivinationRecord(
            question=ctx.question,
            bazi=ctx.bazi,
            birth_datetime=ctx.birth_datetime,
            method=self._last_result.method_desc,
            divination_time=self._last_result.divination_time,
            timezone=ctx.tz.iana_name,
            hexagram=self._last_result.hexagram,
            prompt=self._last_result.prompt,
        )
        path = save_record(record)
        messagebox.showinfo("已保存", f"记录已保存至\n{path}")
        self.status_var.set(f"已保存：{path.name}")

    def _show_settings(self) -> None:
        show_settings_dialog(self)

    def _show_history(self) -> None:
        open_history_window(self, self)

    def _on_close(self) -> None:
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._persist_config_from_form()
        self.destroy()


def main() -> None:
    app = BaguaGuiApp()
    app.mainloop()
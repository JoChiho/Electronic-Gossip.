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
from bagua.gui_dpi import configure_root_dpi, enable_windows_dpi_awareness
from bagua.gui_forms import GuiFormsMixin
from bagua.gui_history import open_history_window
from bagua.gui_settings import show_settings_dialog
from bagua.gui_theme import (
    FONT_HEADER,
    FONT_MONO,
    FONT_PROMPT,
    FONT_SUBTITLE,
    FONT_SYMBOL,
    FONT_UI,
    THEME,
    apply_theme,
    bind_readonly_text,
    style_text_widget,
)
from bagua.models import DivinationRecord, DivinationResult, UserContext
from bagua.records import save_record
from bagua.service import perform_divination
from bagua.timezone import parse_datetime_input


class BaguaGuiApp(GuiFormsMixin, tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} · 易经八卦占卜")

        self._config = load_config()
        self._last_result: DivinationResult | None = None
        self._coin_vars: list[list[tk.StringVar]] = []
        self._autosave_job: str | None = None
        self._loading_form = False
        self._ui_scale = configure_root_dpi(self)

        base_w, base_h = 1120, 900
        self.minsize(int(960 * self._ui_scale), int(780 * self._ui_scale))
        self.geometry(f"{int(base_w * self._ui_scale)}x{int(base_h * self._ui_scale)}")

        apply_theme(self, scale=self._ui_scale)
        self._build_widgets()
        self._load_form_from_config()
        self._bind_autosave()
        self.bind("<Control-Shift-c>", lambda _e: self._copy_prompt())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = tk.Frame(parent, bg=THEME["header_to"], height=int(76 * self._ui_scale))
        header.pack(fill=tk.X, pady=(0, 12))
        header.pack_propagate(False)

        accent = tk.Frame(header, bg=THEME["accent"], width=4)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        text_col = tk.Frame(header, bg=THEME["header_to"])
        text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 12), pady=12)

        tk.Label(
            text_col,
            text=APP_TITLE,
            bg=THEME["header_to"],
            fg=THEME["accent"],
            font=FONT_HEADER,
        ).pack(anchor=tk.W)
        tk.Label(
            text_col,
            text=APP_SUBTITLE,
            bg=THEME["header_to"],
            fg=THEME["text_muted"],
            font=FONT_UI,
        ).pack(anchor=tk.W, pady=(2, 0))
        tk.Label(
            text_col,
            text=DISCLAIMER,
            bg=THEME["header_to"],
            fg=THEME["text_muted"],
            font=FONT_SUBTITLE,
        ).pack(anchor=tk.W, pady=(4, 0))

        right_col = tk.Frame(header, bg=THEME["header_to"])
        right_col.pack(side=tk.RIGHT, padx=16, pady=10)
        ttk.Button(right_col, text="⚙ 设置", command=self._show_settings).pack(anchor=tk.E)
        tk.Label(
            right_col,
            text="☰\n☷",
            bg=THEME["header_to"],
            fg=THEME["accent_dim"],
            font=FONT_SYMBOL,
            justify=tk.CENTER,
        ).pack(pady=(6, 0))

    def _bind_scroll_canvas(self, canvas: tk.Canvas, frame: ttk.Frame) -> None:
        def _on_frame_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(canvas_window, width=event.width)

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_event: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_event: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")

        frame.bind("<Configure>", _on_frame_configure)
        canvas_window = canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        canvas.bind("<Configure>", _on_canvas_configure)
        for widget in (canvas, frame):
            widget.bind("<Enter>", _bind_wheel)
            widget.bind("<Leave>", _unbind_wheel)

    def _build_widgets(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_header(outer)

        content = ttk.Panedwindow(outer, orient=tk.VERTICAL)
        content.pack(fill=tk.BOTH, expand=True)

        top_pane = ttk.Frame(content)
        bottom_pane = ttk.Frame(content)
        content.add(top_pane, weight=2)
        content.add(bottom_pane, weight=3)

        top_pane.rowconfigure(0, weight=1)
        top_pane.columnconfigure(0, weight=0, minsize=int(500 * self._ui_scale))
        top_pane.columnconfigure(1, weight=1)

        left = ttk.Frame(top_pane)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        scroll_canvas = tk.Canvas(
            left, highlightthickness=0, bg=THEME["bg"], borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scroll_frame = ttk.Frame(scroll_canvas)

        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self._bind_scroll_canvas(scroll_canvas, scroll_frame)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_user_section(scroll_frame)
        self._build_method_section(scroll_frame)

        self.options_container = ttk.Frame(scroll_frame)
        self.options_container.pack(fill=tk.X, pady=(0, 4))
        self._build_coin_section(self.options_container)
        self._build_time_section(self.options_container)
        self._build_number_section(self.options_container)
        self._build_manual_section(self.options_container)
        self._build_yarrow_section(self.options_container)
        self._build_character_section(self.options_container)

        self._build_action_section(scroll_frame)

        right = ttk.Frame(top_pane)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._build_result_section(right)

        self._build_prompt_section(bottom_pane)

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
        frame = ttk.LabelFrame(parent, text="  卦象结果  ", style="Section.TLabelframe", padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        inner = ttk.Frame(frame, style="Card.TFrame")
        inner.pack(fill=tk.BOTH, expand=True)

        canvas_w = int(260 * self._ui_scale)
        canvas_h = int(280 * self._ui_scale)
        canvas_col = ttk.Frame(inner, style="Card.TFrame")
        canvas_col.pack(side=tk.LEFT, fill=tk.Y)
        self.hexagram_canvas = HexagramCanvas(
            canvas_col, width=canvas_w, height=canvas_h, ui_scale=self._ui_scale,
        )
        self.hexagram_canvas.pack(fill=tk.Y)
        self.hexagram_canvas.draw_hexagram(None)

        text_col = ttk.Frame(inner, style="Card.TFrame")
        text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0))
        self.result_text = scrolledtext.ScrolledText(
            text_col, height=10, wrap=tk.WORD, font=FONT_MONO,
        )
        style_text_widget(self.result_text, readonly=True)
        bind_readonly_text(self.result_text)
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _build_prompt_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(
            parent, text="  AI 解读提示词  ", style="PromptCard.TLabelframe", padding=0,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(frame, bg=THEME["surface_alt"], height=int(52 * self._ui_scale))
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text="起卦后复制下方全文，粘贴至 ChatGPT / Claude 等大模型解读",
            bg=THEME["surface_alt"],
            fg=THEME["text_muted"],
            font=FONT_SUBTITLE,
        ).pack(side=tk.LEFT, padx=(14, 0), pady=14)

        self.prompt_stats_var = tk.StringVar(value="")
        tk.Label(
            toolbar,
            textvariable=self.prompt_stats_var,
            bg=THEME["surface_alt"],
            fg=THEME["text_muted"],
            font=FONT_SUBTITLE,
        ).pack(side=tk.LEFT, padx=(12, 0), pady=14)

        btn_group = ttk.Frame(toolbar, style="Toolbar.TFrame")
        btn_group.pack(side=tk.RIGHT, padx=12, pady=8)
        ttk.Button(
            btn_group,
            text="📋  复制到剪贴板",
            style="Accent.TButton",
            command=self._copy_prompt,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_group, text="保存记录", command=self._save_record).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(
            btn_group, text="历史记录", style="Ghost.TButton", command=self._show_history,
        ).pack(side=tk.RIGHT)

        body = ttk.Frame(frame, padding=(12, 10, 12, 12))
        body.pack(fill=tk.BOTH, expand=True)

        self.prompt_text = scrolledtext.ScrolledText(
            body, wrap=tk.WORD, font=FONT_PROMPT, spacing1=2, spacing3=4,
        )
        style_text_widget(self.prompt_text)
        bind_readonly_text(self.prompt_text)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)

        placeholder = (
            "点击「起卦」后，完整 AI 解读提示词将显示在此区域。\n"
            "可使用顶部「复制到剪贴板」按钮一键复制（快捷键 Ctrl+Shift+C）。"
        )
        self._set_text_widget(self.prompt_text, placeholder)
        self._update_prompt_stats(0)

    def _update_prompt_stats(self, length: int) -> None:
        if length <= 0:
            self.prompt_stats_var.set("")
            return
        lines = int(self.prompt_text.index("end-1c").split(".")[0])
        self.prompt_stats_var.set(f"{length} 字 · {lines} 行")

    def _set_text_widget(self, widget: scrolledtext.ScrolledText, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        if widget is self.result_text:
            widget.configure(state=tk.NORMAL)
            bind_readonly_text(widget)

    def _on_divinate(self) -> None:
        try:
            loc_err = self._validate_location_fields()
            if loc_err:
                messagebox.showerror("输入错误", loc_err)
                return
            ctx = self._build_context()
            method = cast(
                Literal["coin", "time", "random", "number", "manual", "yarrow", "character"],
                self.method_var.get(),
            )
            coin_tosses = None
            divination_dt = None
            number_inputs = None
            manual_upper = manual_lower = manual_changing = None
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
                        divination_dt = parse_datetime_input(raw, ctx.divination_tz)
                        if divination_dt is None:
                            messagebox.showerror("输入错误", "公历时间格式无效，请使用如 2026-06-24 14:30")
                            return
                if ctx.calendar_mode == "lunar" and lunar_input:
                    ctx = UserContext(
                        question=ctx.question,
                        bazi=ctx.bazi,
                        birth_datetime=ctx.birth_datetime,
                        birth_tz=ctx.birth_tz,
                        divination_tz=ctx.divination_tz,
                        coin_mode=ctx.coin_mode,
                        calendar_mode=ctx.calendar_mode,
                        lunar_input=lunar_input,
                        include_hexagram_texts=ctx.include_hexagram_texts,
                        birth_longitude=ctx.birth_longitude,
                        divination_longitude=ctx.divination_longitude,
                        use_true_solar_birth=ctx.use_true_solar_birth,
                        use_true_solar_divination=ctx.use_true_solar_divination,
                    )
            elif method == "number":
                number_inputs = self._collect_number_inputs()
                if number_inputs is None:
                    messagebox.showerror(
                        "输入错误",
                        "请填写第一、第二数（正整数）；第三数可选，用于指定动爻",
                    )
                    return
            elif method == "manual":
                manual_sel = self._collect_manual_selection()
                if manual_sel is None:
                    messagebox.showerror("输入错误", "请选择有效的上卦与下卦")
                    return
                manual_upper, manual_lower, manual_changing = manual_sel

            character_text = None
            if method == "character":
                character_text = self._collect_character_text()
                if character_text is None:
                    messagebox.showerror("输入错误", "请输入至少一个汉字")
                    return

            result = perform_divination(
                method,
                ctx,
                coin_tosses=coin_tosses,
                divination_datetime=divination_dt,
                number_inputs=number_inputs,
                manual_upper=manual_upper,
                manual_lower=manual_lower,
                manual_changing=manual_changing,
                coin_mode=coin_mode,
                auto_bazi=self._config.auto_bazi,
                yarrow_show_process=self.yarrow_show_process_var.get(),
                character_text=character_text,
                character_strategy=self._character_strategy_key(),
                character_stroke_mode=self._character_stroke_mode_key(),
            )
            self._last_result = result

            result_lines = [
                f"起卦时间：{result.divination_time}",
                f"起卦方法：{result.method_desc}",
                "",
                format_hexagram_display(result.hexagram),
            ]
            if result.process_log:
                result_lines.extend(["", result.process_log])
            if method == "yarrow" and self.yarrow_show_process_var.get():
                self._set_yarrow_process_text(result.process_log or "")
            self._set_text_widget(self.result_text, "\n".join(result_lines))
            self._set_text_widget(self.prompt_text, result.prompt)
            self.prompt_text.see("1.0")
            self._update_prompt_stats(len(result.prompt))
            self.hexagram_canvas.draw_hexagram(result.hexagram)

            self._persist_config_from_form()
            if self._config.auto_copy_prompt and copy_to_clipboard(result.prompt):
                self.status_var.set("起卦完成 · 提示词已复制到剪贴板")
            else:
                self.status_var.set("起卦完成 · 可点击「复制到剪贴板」")
        except Exception as exc:
            messagebox.showerror("起卦失败", str(exc))
            self.status_var.set("起卦失败")

    def _copy_prompt(self) -> None:
        text = ""
        if self._last_result and self._last_result.prompt.strip():
            text = self._last_result.prompt
        else:
            text = self.prompt_text.get("1.0", tk.END).strip()
            if text.startswith("点击「起卦」后"):
                text = ""
        if not text:
            messagebox.showinfo("提示", "请先起卦，生成 AI 提示词后再复制")
            return
        if copy_to_clipboard(text):
            self.status_var.set(f"已复制 {len(text)} 字到剪贴板")
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
            timezone=ctx.divination_tz.iana_name,
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
    enable_windows_dpi_awareness()
    app = BaguaGuiApp()
    app.mainloop()
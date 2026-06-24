"""bagua Tkinter 图形界面。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from bagua.config import load_config, save_config, save_record
from bagua.divination import tosses_to_yao_value
from bagua.gui_display import format_hexagram_display
from bagua.models import DivinationRecord, UserConfig, UserContext
from bagua.service import perform_divination
from bagua.timezone import (
    TIMEZONE_PRESETS,
    detect_system_timezone_name,
    get_timezone,
    label_for_timezone,
    parse_datetime_input,
)

APP_TITLE = "bagua · 易经八卦占卜"
DISCLAIMER = "仅供娱乐与文化学习参考，不构成任何决策依据。"


class BaguaGuiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(760, 720)
        self.geometry("820x780")

        self._config = load_config()
        self._last_result = None
        self._coin_vars: list[list[tk.StringVar]] = []

        self._setup_style()
        self._build_widgets()
        self._load_form_from_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 14, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TButton", padding=6)
        style.configure("Accent.TButton", padding=8)

    def _build_widgets(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(outer, text=DISCLAIMER, foreground="#666666").pack(anchor=tk.W, pady=(0, 8))

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_user_section(scroll_frame)
        self._build_method_section(scroll_frame)

        self.options_container = ttk.Frame(scroll_frame)
        self.options_container.pack(fill=tk.X, pady=(0, 8))
        self._build_coin_section(self.options_container)
        self._build_time_section(self.options_container)

        self._build_action_section(scroll_frame)
        self._build_result_section(scroll_frame)
        self._build_prompt_section(scroll_frame)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self._on_method_changed()
        self._on_coin_mode_changed()

    def _build_user_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="用户信息", style="Section.TLabelframe", padding=10)
        frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frame, text="占卜问题").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.question_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.question_var, width=60).grid(
            row=0, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0)
        )

        ttk.Label(frame, text="生辰八字").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.bazi_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.bazi_var, width=60).grid(
            row=1, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0)
        )

        ttk.Label(frame, text="出生时间").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.birth_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.birth_var, width=30).grid(
            row=2, column=1, sticky=tk.W, padx=(8, 0)
        )
        ttk.Label(frame, text="如 1990-01-01 08:00", foreground="#666666").grid(
            row=2, column=2, sticky=tk.W, padx=(8, 0)
        )

        ttk.Label(frame, text="时区").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.tz_display_var = tk.StringVar()
        self.tz_combo = ttk.Combobox(
            frame,
            textvariable=self.tz_display_var,
            values=[label for _, label in TIMEZONE_PRESETS],
            state="readonly",
            width=40,
        )
        self.tz_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(8, 0))
        self.tz_combo.bind("<<ComboboxSelected>>", lambda _e: None)

        frame.columnconfigure(1, weight=1)

    def _build_method_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="起卦方式", style="Section.TLabelframe", padding=10)
        frame.pack(fill=tk.X, pady=(0, 8))

        self.method_var = tk.StringVar(value="coin")
        for i, (val, label) in enumerate([("coin", "铜钱法"), ("time", "时间起卦"), ("random", "随机起卦")]):
            ttk.Radiobutton(
                frame,
                text=label,
                variable=self.method_var,
                value=val,
                command=self._on_method_changed,
            ).grid(row=0, column=i, padx=(0, 16), sticky=tk.W)

        ttk.Label(frame, text="铜钱模式").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.coin_mode_var = tk.StringVar(value="manual")
        ttk.Radiobutton(
            frame,
            text="手动（1=阳 2=阴）",
            variable=self.coin_mode_var,
            value="manual",
            command=self._on_coin_mode_changed,
        ).grid(row=1, column=1, sticky=tk.W, pady=(8, 0))
        ttk.Radiobutton(
            frame,
            text="自动模拟",
            variable=self.coin_mode_var,
            value="auto",
            command=self._on_coin_mode_changed,
        ).grid(row=1, column=2, sticky=tk.W, pady=(8, 0))

    def _build_coin_section(self, parent: ttk.Frame) -> None:
        self.coin_frame = ttk.LabelFrame(
            parent, text="铜钱手动输入（每爻三个 1 或 2）", style="Section.TLabelframe", padding=10
        )
        self.coin_frame.pack(fill=tk.X, pady=(0, 8))

        from bagua.data import YAO_POSITIONS

        self._coin_vars.clear()
        for row, pos_name in enumerate(YAO_POSITIONS):
            ttk.Label(self.coin_frame, text=pos_name, width=6).grid(row=row, column=0, sticky=tk.W, pady=2)
            row_vars: list[tk.StringVar] = []
            for col in range(3):
                var = tk.StringVar(value="1")
                row_vars.append(var)
                ttk.Combobox(
                    self.coin_frame,
                    textvariable=var,
                    values=["1", "2"],
                    width=4,
                    state="readonly",
                ).grid(row=row, column=col + 1, padx=4, pady=2)
            self._coin_vars.append(row_vars)

    def _build_time_section(self, parent: ttk.Frame) -> None:
        self.time_frame = ttk.LabelFrame(
            parent, text="时间起卦", style="Section.TLabelframe", padding=10
        )
        self.time_frame.pack(fill=tk.X, pady=(0, 8))

        self.use_now_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.time_frame,
            text="使用当前时间",
            variable=self.use_now_var,
            command=self._on_use_now_changed,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(self.time_frame, text="指定时间").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.time_input_var = tk.StringVar()
        self.time_entry = ttk.Entry(self.time_frame, textvariable=self.time_input_var, width=28)
        self.time_entry.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=(8, 0))
        ttk.Label(self.time_frame, text="如 2026-06-24 14:30", foreground="#666666").grid(
            row=1, column=2, sticky=tk.W, padx=(8, 0)
        )
        self._on_use_now_changed()

    def _build_action_section(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(frame, text="起 卦", style="Accent.TButton", command=self._on_divinate).pack(
            side=tk.LEFT
        )

    def _build_result_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="卦象结果", style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.result_text = scrolledtext.ScrolledText(
            frame, height=12, wrap=tk.WORD, font=("Consolas", 11), state=tk.DISABLED
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _build_prompt_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="AI 解读提示词", style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        self.prompt_text = scrolledtext.ScrolledText(
            frame, height=14, wrap=tk.WORD, font=("Microsoft YaHei UI", 10)
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="复制提示词", command=self._copy_prompt).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="保存记录", command=self._save_record).pack(side=tk.LEFT, padx=(8, 0))

    def _on_method_changed(self) -> None:
        method = self.method_var.get()
        self.coin_frame.pack_forget()
        self.time_frame.pack_forget()
        if method == "coin":
            self.coin_frame.pack(fill=tk.X, pady=(0, 4))
            self._on_coin_mode_changed()
        elif method == "time":
            self.time_frame.pack(fill=tk.X, pady=(0, 4))

    def _on_coin_mode_changed(self) -> None:
        if self.method_var.get() != "coin":
            return
        manual = self.coin_mode_var.get() == "manual"
        state = "readonly" if manual else "disabled"
        for child in self.coin_frame.winfo_children():
            if isinstance(child, ttk.Combobox):
                child.configure(state=state)

    def _on_use_now_changed(self) -> None:
        state = "disabled" if self.use_now_var.get() else "normal"
        self.time_entry.configure(state=state)

    def _selected_timezone(self) -> tuple[str, str]:
        label = self.tz_display_var.get()
        for iana, preset_label in TIMEZONE_PRESETS:
            if preset_label == label:
                return iana, preset_label
        return self._config.timezone, self._config.region_label

    def _build_context(self) -> UserContext:
        iana, region = self._selected_timezone()
        tz = get_timezone(iana, region)
        return UserContext(
            question=self.question_var.get().strip(),
            bazi=self.bazi_var.get().strip(),
            birth_datetime=self.birth_var.get().strip(),
            tz=tz,
            coin_mode=self.coin_mode_var.get(),
        )

    def _collect_coin_tosses(self) -> list[list[int]] | None:
        if self.coin_mode_var.get() == "auto":
            return None
        tosses: list[list[int]] = []
        for row_vars in self._coin_vars:
            points = [3 if v.get() == "1" else 2 for v in row_vars]
            tosses_to_yao_value(points)
            tosses.append(points)
        return tosses

    def _set_text_widget(self, widget: scrolledtext.ScrolledText, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        if widget is self.result_text:
            widget.configure(state=tk.DISABLED)

    def _on_divinate(self) -> None:
        try:
            ctx = self._build_context()
            method = self.method_var.get()
            coin_tosses = None
            divination_dt = None
            coin_mode = self.coin_mode_var.get()

            if method == "coin":
                coin_tosses = self._collect_coin_tosses()
            elif method == "time":
                if not self.use_now_var.get():
                    raw = self.time_input_var.get().strip()
                    divination_dt = parse_datetime_input(raw, ctx.tz)
                    if divination_dt is None:
                        messagebox.showerror("输入错误", "时间格式无效，请使用如 2026-06-24 14:30")
                        return

            result = perform_divination(
                method,
                ctx,
                coin_tosses=coin_tosses,
                divination_datetime=divination_dt,
                coin_mode=coin_mode,
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

            self._persist_config_from_form()
            self.status_var.set("起卦完成")
        except Exception as exc:
            messagebox.showerror("起卦失败", str(exc))
            self.status_var.set("起卦失败")

    def _copy_prompt(self) -> None:
        text = self.prompt_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("提示", "暂无提示词可复制")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.status_var.set("已复制到剪贴板")

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

    def _load_form_from_config(self) -> None:
        cfg = self._config
        if not cfg.timezone or cfg.timezone == "Asia/Shanghai":
            detected = detect_system_timezone_name()
            if detected != "Asia/Shanghai":
                cfg.timezone = detected
                cfg.region_label = label_for_timezone(detected)

        self.question_var.set(cfg.question)
        self.bazi_var.set(cfg.bazi)
        self.birth_var.set(cfg.birth_datetime)
        self.coin_mode_var.set(cfg.coin_mode if cfg.coin_mode in ("manual", "auto") else "manual")

        labels = [label for _, label in TIMEZONE_PRESETS]
        if cfg.region_label in labels:
            self.tz_display_var.set(cfg.region_label)
        else:
            self.tz_display_var.set(TIMEZONE_PRESETS[0][1])

    def _persist_config_from_form(self) -> None:
        iana, region = self._selected_timezone()
        self._config = UserConfig(
            timezone=iana,
            region_label=region,
            question=self.question_var.get().strip(),
            bazi=self.bazi_var.get().strip(),
            birth_datetime=self.birth_var.get().strip(),
            coin_mode=self.coin_mode_var.get(),
        )
        save_config(self._config)

    def _on_close(self) -> None:
        self._persist_config_from_form()
        self.destroy()


def main() -> None:
    app = BaguaGuiApp()
    app.mainloop()


if __name__ == "__main__":
    main()
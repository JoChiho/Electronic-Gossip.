"""GUI 表单构建、自动保存与配置读写。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from bagua.bazi import compute_bazi
from bagua.config import CONFIG_PATH, save_config
from bagua.divination import tosses_to_yao_value
from bagua.models import UserConfig, UserContext
from bagua.timezone import (
    TIMEZONE_PRESETS,
    detect_system_timezone_name,
    get_timezone,
    label_for_timezone,
)


class GuiFormsMixin:
    """表单区与 config 持久化逻辑，供 BaguaGuiApp 混入。"""

    _config: UserConfig
    _coin_vars: list[list[tk.StringVar]]
    _autosave_job: str | None
    _loading_form: bool
    status_var: tk.StringVar
    question_var: tk.StringVar
    bazi_var: tk.StringVar
    birth_var: tk.StringVar
    tz_display_var: tk.StringVar
    tz_combo: ttk.Combobox
    method_var: tk.StringVar
    coin_mode_var: tk.StringVar
    coin_frame: ttk.LabelFrame
    time_frame: ttk.LabelFrame
    use_now_var: tk.BooleanVar
    calendar_var: tk.StringVar
    time_input_var: tk.StringVar
    time_entry: ttk.Entry
    time_hint_label: ttk.Label

    def _section(self, parent: ttk.Frame, title: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=f"  {title}  ", style="Section.TLabelframe", padding=14)
        frame.pack(fill=tk.X, pady=(0, 10))
        return frame

    def _build_user_section(self, parent: ttk.Frame) -> None:
        frame = self._section(parent, "个人信息")

        ttk.Label(frame, text="占卜问题", style="Field.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.question_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.question_var).grid(
            row=0, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0)
        )

        ttk.Label(frame, text="生辰八字", style="Field.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.bazi_var = tk.StringVar()
        bazi_row = ttk.Frame(frame, style="Card.TFrame")
        bazi_row.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0))
        ttk.Entry(bazi_row, textvariable=self.bazi_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bazi_row, text="自动排盘", command=self._auto_bazi).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(frame, text="出生时间", style="Field.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.birth_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.birth_var, width=28).grid(
            row=2, column=1, sticky=tk.W, padx=(10, 0)
        )
        ttk.Label(frame, text="如 1990-01-01 08:00", style="Muted.TLabel").grid(
            row=2, column=2, sticky=tk.W, padx=(8, 0)
        )

        ttk.Label(frame, text="时区", style="Field.TLabel").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.tz_display_var = tk.StringVar()
        self.tz_combo = ttk.Combobox(
            frame,
            textvariable=self.tz_display_var,
            values=[label for _, label in TIMEZONE_PRESETS],
            state="readonly",
            width=36,
        )
        self.tz_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))
        frame.columnconfigure(1, weight=1)

    def _build_method_section(self, parent: ttk.Frame) -> None:
        frame = self._section(parent, "起卦方式")

        self.method_var = tk.StringVar(value="coin")
        methods = [("coin", "铜钱法"), ("time", "时间起卦"), ("random", "随机起卦")]
        method_row = ttk.Frame(frame, style="Card.TFrame")
        method_row.grid(row=0, column=0, columnspan=3, sticky=tk.W)
        for val, label in methods:
            ttk.Radiobutton(
                method_row,
                text=label,
                variable=self.method_var,
                value=val,
                command=self._on_method_changed,
            ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(frame, text="铜钱模式", style="Field.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.coin_mode_var = tk.StringVar(value="manual")
        coin_row = ttk.Frame(frame, style="Card.TFrame")
        coin_row.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        for val, label in [("manual", "手动（1=阳 2=阴）"), ("auto", "自动模拟")]:
            ttk.Radiobutton(
                coin_row,
                text=label,
                variable=self.coin_mode_var,
                value=val,
                command=self._on_coin_mode_changed,
            ).pack(side=tk.LEFT, padx=(0, 16))

    def _build_coin_section(self, parent: ttk.Frame) -> None:
        self.coin_frame = ttk.LabelFrame(
            parent, text="  铜钱手动输入  ", style="Section.TLabelframe", padding=12
        )
        self.coin_frame.pack(fill=tk.X, pady=(0, 8))

        from bagua.data import YAO_POSITIONS

        self._coin_vars.clear()
        for row, pos_name in enumerate(YAO_POSITIONS):
            ttk.Label(self.coin_frame, text=pos_name, style="Field.TLabel", width=6).grid(
                row=row, column=0, sticky=tk.W, pady=3
            )
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
                ).grid(row=row, column=col + 1, padx=5, pady=3)
            self._coin_vars.append(row_vars)

    def _build_time_section(self, parent: ttk.Frame) -> None:
        self.time_frame = ttk.LabelFrame(
            parent, text="  时间起卦  ", style="Section.TLabelframe", padding=12
        )
        self.time_frame.pack(fill=tk.X, pady=(0, 8))

        self.use_now_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.time_frame,
            text="使用当前时间",
            variable=self.use_now_var,
            command=self._on_use_now_changed,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(self.time_frame, text="历法", style="Field.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.calendar_var = tk.StringVar(value="solar")
        cal_row = ttk.Frame(self.time_frame, style="Card.TFrame")
        cal_row.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Radiobutton(
            cal_row, text="公历", variable=self.calendar_var, value="solar",
            command=self._on_calendar_changed,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            cal_row, text="农历", variable=self.calendar_var, value="lunar",
            command=self._on_calendar_changed,
        ).pack(side=tk.LEFT, padx=(14, 0))

        ttk.Label(self.time_frame, text="指定时间", style="Field.TLabel").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.time_input_var = tk.StringVar()
        self.time_entry = ttk.Entry(self.time_frame, textvariable=self.time_input_var, width=26)
        self.time_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        self.time_hint_label = ttk.Label(
            self.time_frame,
            text="公历，如 2026-06-24 14:30（算卦自动换算节气历）",
            style="Muted.TLabel",
        )
        self.time_hint_label.grid(row=2, column=2, sticky=tk.W, padx=(8, 0))

    def _bind_autosave(self) -> None:
        for var in (
            self.question_var,
            self.bazi_var,
            self.birth_var,
            self.tz_display_var,
            self.method_var,
            self.coin_mode_var,
            self.calendar_var,
            self.time_input_var,
        ):
            var.trace_add("write", lambda *_: self._schedule_save())
        self.use_now_var.trace_add("write", lambda *_: self._schedule_save())
        for row in self._coin_vars:
            for var in row:
                var.trace_add("write", lambda *_: self._schedule_save())
        self.tz_combo.bind("<<ComboboxSelected>>", lambda _e: self._schedule_save())

    def _schedule_save(self) -> None:
        if self._loading_form:
            return
        if self._autosave_job:
            self.after_cancel(self._autosave_job)  # type: ignore[attr-defined]
        self._autosave_job = self.after(600, self._autosave)  # type: ignore[attr-defined]

    def _autosave(self) -> None:
        self._autosave_job = None
        self._persist_config_from_form()
        if CONFIG_PATH.exists():
            self.status_var.set(f"已自动保存 · {CONFIG_PATH.name}")

    def _on_method_changed(self) -> None:
        method = self.method_var.get()
        self.coin_frame.pack_forget()
        self.time_frame.pack_forget()
        if method == "coin":
            self.coin_frame.pack(fill=tk.X, pady=(0, 4))
            self._on_coin_mode_changed()
        elif method == "time":
            self.time_frame.pack(fill=tk.X, pady=(0, 4))
        self._schedule_save()

    def _on_coin_mode_changed(self) -> None:
        if self.method_var.get() != "coin":
            return
        manual = self.coin_mode_var.get() == "manual"
        state = "readonly" if manual else "disabled"
        for child in self.coin_frame.winfo_children():
            if isinstance(child, ttk.Combobox):
                child.configure(state=state)
        self._schedule_save()

    def _on_use_now_changed(self) -> None:
        state = "disabled" if self.use_now_var.get() else "normal"
        self.time_entry.configure(state=state)
        self._schedule_save()

    def _on_calendar_changed(self) -> None:
        if self.calendar_var.get() == "lunar":
            self.time_hint_label.configure(text="农历，如 2026-05-10 14:30")
        else:
            self.time_hint_label.configure(
                text="公历，如 2026-06-24 14:30（算卦自动换算节气历）",
            )
        self._schedule_save()

    def _auto_bazi(self) -> None:
        birth = self.birth_var.get().strip()
        if not birth:
            messagebox.showinfo("提示", "请先填写出生时间")
            return
        iana, region = self._selected_timezone()
        tz = get_timezone(iana, region)
        computed = compute_bazi(birth, tz)
        if not computed:
            messagebox.showwarning("排盘失败", "无法解析出生时间，请检查格式与时区")
            return
        self.bazi_var.set(computed)
        self.status_var.set("已自动排八字")

    def _selected_timezone(self) -> tuple[str, str]:
        label = self.tz_display_var.get()
        for iana, preset_label in TIMEZONE_PRESETS:
            if preset_label == label:
                return iana, preset_label
        return self._config.timezone, self._config.region_label

    def _collect_coin_tosses_state(self) -> list[list[str]]:
        return [[v.get() for v in row] for row in self._coin_vars]

    def _build_context(self) -> UserContext:
        iana, region = self._selected_timezone()
        tz = get_timezone(iana, region)
        return UserContext(
            question=self.question_var.get().strip(),
            bazi=self.bazi_var.get().strip(),
            birth_datetime=self.birth_var.get().strip(),
            tz=tz,
            coin_mode=self.coin_mode_var.get(),
            calendar_mode=self.calendar_var.get(),
            include_hexagram_texts=self._config.include_hexagram_texts,
            longitude=self._config.longitude,
            use_true_solar=self._config.use_true_solar,
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

    def _load_coin_tosses_from_config(self, cfg: UserConfig) -> None:
        stored = cfg.coin_tosses or []
        for i, row_vars in enumerate(self._coin_vars):
            row_data = stored[i] if i < len(stored) else ["1", "1", "1"]
            for j, var in enumerate(row_vars):
                val = row_data[j] if j < len(row_data) else "1"
                var.set(val if val in ("1", "2") else "1")

    def _load_form_from_config(self) -> None:
        self._loading_form = True
        try:
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
            self.calendar_var.set(cfg.calendar_mode if cfg.calendar_mode in ("solar", "lunar") else "solar")
            self.method_var.set(cfg.last_method if cfg.last_method in ("coin", "time", "random") else "coin")
            self.use_now_var.set(cfg.use_current_time)
            self.time_input_var.set(cfg.time_input)
            self._load_coin_tosses_from_config(cfg)

            labels = [label for _, label in TIMEZONE_PRESETS]
            if cfg.region_label in labels:
                self.tz_display_var.set(cfg.region_label)
            else:
                self.tz_display_var.set(TIMEZONE_PRESETS[0][1])

            self._on_method_changed()
            self._on_use_now_changed()
            self._on_calendar_changed()
        finally:
            self._loading_form = False

    def _persist_config_from_form(self) -> None:
        iana, region = self._selected_timezone()
        self._config = UserConfig(
            timezone=iana,
            region_label=region,
            question=self.question_var.get().strip(),
            bazi=self.bazi_var.get().strip(),
            birth_datetime=self.birth_var.get().strip(),
            coin_mode=self.coin_mode_var.get(),
            calendar_mode=self.calendar_var.get(),
            auto_bazi=self._config.auto_bazi,
            auto_copy_prompt=self._config.auto_copy_prompt,
            include_hexagram_texts=self._config.include_hexagram_texts,
            last_method=self.method_var.get(),
            use_current_time=self.use_now_var.get(),
            time_input=self.time_input_var.get().strip(),
            coin_tosses=self._collect_coin_tosses_state(),
            longitude=self._config.longitude,
            use_true_solar=self._config.use_true_solar,
        )
        save_config(self._config)
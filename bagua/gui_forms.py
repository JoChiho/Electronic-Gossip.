"""GUI 表单构建、自动保存与配置读写。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from bagua.bazi import compute_bazi
from bagua.character import CHARACTER_STRATEGIES, STRATEGY_LABELS, resolve_strokes
from bagua.config import CONFIG_PATH, save_config
from bagua.data import MANUAL_CHANGING_OPTIONS, TRIGRAM_SELECT_OPTIONS
from bagua.divination import (
    parse_manual_changing,
    parse_number_input,
    parse_trigram_index,
    tosses_to_yao_value,
)
from bagua.locations import (
    LOCATION_CUSTOM,
    LOCATION_FOLLOW_TZ,
    LOCATION_OPTIONS,
    default_city_for_timezone,
    display_coord_hint,
    format_latitude,
    infer_location_label,
    parse_longitude,
    resolve_display_coord,
    resolve_longitude,
)
from bagua.models import UserConfig, UserContext
from bagua.stroke_data import STROKE_MODE_LABELS, STROKE_MODES, format_stroke_preview
from bagua.timezone import (
    TIMEZONE_PRESETS,
    detect_system_timezone_name,
    get_timezone,
    label_for_timezone,
)
from bagua.true_solar import default_longitude


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
    div_tz_display_var: tk.StringVar
    div_tz_combo: ttk.Combobox
    method_var: tk.StringVar
    coin_mode_var: tk.StringVar
    coin_frame: ttk.LabelFrame
    time_frame: ttk.LabelFrame
    number_frame: ttk.LabelFrame
    number_n1_var: tk.StringVar
    number_n2_var: tk.StringVar
    number_n3_var: tk.StringVar
    manual_frame: ttk.LabelFrame
    manual_upper_var: tk.StringVar
    manual_lower_var: tk.StringVar
    manual_changing_var: tk.StringVar
    yarrow_frame: ttk.LabelFrame
    yarrow_show_process_var: tk.BooleanVar
    yarrow_process_frame: ttk.LabelFrame
    yarrow_process_text: tk.Text
    character_frame: ttk.LabelFrame
    character_input_var: tk.StringVar
    character_strategy_var: tk.StringVar
    character_stroke_mode_var: tk.StringVar
    character_preview_var: tk.StringVar
    use_now_var: tk.BooleanVar
    calendar_var: tk.StringVar
    time_input_var: tk.StringVar
    time_entry: ttk.Entry
    time_hint_label: ttk.Label
    birth_location_var: tk.StringVar
    birth_lon_var: tk.StringVar
    birth_lat_var: tk.StringVar
    birth_coord_hint: ttk.Label
    use_true_solar_birth_var: tk.BooleanVar
    div_location_var: tk.StringVar
    div_lon_var: tk.StringVar
    div_lat_var: tk.StringVar
    div_coord_hint: ttk.Label
    use_true_solar_div_var: tk.BooleanVar

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

        ttk.Label(frame, text="出生时区", style="Field.TLabel").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.tz_display_var = tk.StringVar()
        self.tz_combo = ttk.Combobox(
            frame,
            textvariable=self.tz_display_var,
            values=[label for _, label in TIMEZONE_PRESETS],
            state="readonly",
            width=36,
        )
        self.tz_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))
        self.tz_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_birth_tz_changed())

        ttk.Label(frame, text="出生地点", style="Field.TLabel").grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
        self.birth_location_var = tk.StringVar(value=LOCATION_FOLLOW_TZ)
        self.birth_location_combo = ttk.Combobox(
            frame,
            textvariable=self.birth_location_var,
            values=LOCATION_OPTIONS,
            state="readonly",
            width=18,
        )
        self.birth_location_combo.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        self.birth_location_combo.bind("<<ComboboxSelected>>", self._on_birth_location_selected)

        ttk.Label(frame, text="出生地坐标", style="Field.TLabel").grid(row=5, column=0, sticky=tk.W, pady=(8, 0))
        coord_row = ttk.Frame(frame, style="Card.TFrame")
        coord_row.grid(row=5, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=(8, 0))
        ttk.Label(coord_row, text="经度", style="Muted.TLabel").pack(side=tk.LEFT)
        self.birth_lon_var = tk.StringVar()
        self.birth_lon_entry = ttk.Entry(coord_row, textvariable=self.birth_lon_var, width=10)
        self.birth_lon_entry.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(coord_row, text="纬度", style="Muted.TLabel").pack(side=tk.LEFT)
        self.birth_lat_var = tk.StringVar(value="—")
        ttk.Label(coord_row, textvariable=self.birth_lat_var, style="Field.TLabel", width=14).pack(
            side=tk.LEFT, padx=(4, 0),
        )
        self.birth_coord_hint = ttk.Label(frame, text="", style="Muted.TLabel")
        self.birth_coord_hint.grid(row=6, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))

        self.use_true_solar_birth_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="八字排盘使用出生地真太阳时",
            variable=self.use_true_solar_birth_var,
        ).grid(row=7, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(8, 0))
        ttk.Label(
            frame,
            text="真太阳时校正仅使用经度；纬度用于确认所选城市（不影响演卦）",
            style="Muted.TLabel",
        ).grid(row=8, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))

        frame.columnconfigure(1, weight=1)

    def _show_method_help(self) -> None:
        from bagua.gui_method_help import show_method_help_dialog

        show_method_help_dialog(self, current_method=self.method_var.get())

    def _build_method_section(self, parent: ttk.Frame) -> None:
        frame = self._section(parent, "起卦方式")

        header = ttk.Frame(frame, style="Card.TFrame")
        header.grid(row=0, column=0, columnspan=3, sticky=tk.EW)
        ttk.Button(header, text="起卦说明", command=self._show_method_help).pack(side=tk.RIGHT)

        self.method_var = tk.StringVar(value="coin")
        methods = [
            ("coin", "铜钱法"),
            ("time", "时间起卦"),
            ("random", "随机起卦"),
            ("number", "数字起卦"),
            ("manual", "手动选卦"),
            ("yarrow", "蓍草法"),
            ("character", "汉字起卦"),
        ]
        method_grid = ttk.Frame(frame, style="Card.TFrame")
        method_grid.grid(row=1, column=0, columnspan=3, sticky=tk.EW)
        cols_per_row = 4
        for i, (val, label) in enumerate(methods):
            ttk.Radiobutton(
                method_grid,
                text=label,
                variable=self.method_var,
                value=val,
                command=self._on_method_changed,
            ).grid(row=i // cols_per_row, column=i % cols_per_row, sticky=tk.W, padx=(0, 12), pady=2)

        self.coin_mode_var = tk.StringVar(value="manual")
        self.coin_mode_frame = ttk.Frame(frame, style="Card.TFrame")
        self.coin_mode_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        ttk.Label(self.coin_mode_frame, text="铜钱模式", style="Field.TLabel").pack(side=tk.LEFT)
        coin_row = ttk.Frame(self.coin_mode_frame, style="Card.TFrame")
        coin_row.pack(side=tk.LEFT, padx=(10, 0))
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

        ttk.Label(self.time_frame, text="起卦时区", style="Field.TLabel").grid(
            row=3, column=0, sticky=tk.W, pady=(10, 0),
        )
        self.div_tz_display_var = tk.StringVar()
        self.div_tz_combo = ttk.Combobox(
            self.time_frame,
            textvariable=self.div_tz_display_var,
            values=[label for _, label in TIMEZONE_PRESETS],
            state="readonly",
            width=32,
        )
        self.div_tz_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(
            self.time_frame,
            text="可与出生地不同，如北京出生、东京起卦",
            style="Muted.TLabel",
        ).grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))
        self.div_tz_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_div_tz_changed())

        ttk.Label(self.time_frame, text="起卦地点", style="Field.TLabel").grid(
            row=5, column=0, sticky=tk.W, pady=(10, 0),
        )
        self.div_location_var = tk.StringVar(value=LOCATION_FOLLOW_TZ)
        self.div_location_combo = ttk.Combobox(
            self.time_frame,
            textvariable=self.div_location_var,
            values=LOCATION_OPTIONS,
            state="readonly",
            width=18,
        )
        self.div_location_combo.grid(row=5, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        self.div_location_combo.bind("<<ComboboxSelected>>", self._on_div_location_selected)

        ttk.Label(self.time_frame, text="起卦地坐标", style="Field.TLabel").grid(
            row=6, column=0, sticky=tk.W, pady=(8, 0),
        )
        div_coord_row = ttk.Frame(self.time_frame, style="Card.TFrame")
        div_coord_row.grid(row=6, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=(8, 0))
        ttk.Label(div_coord_row, text="经度", style="Muted.TLabel").pack(side=tk.LEFT)
        self.div_lon_var = tk.StringVar()
        self.div_lon_entry = ttk.Entry(div_coord_row, textvariable=self.div_lon_var, width=10)
        self.div_lon_entry.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(div_coord_row, text="纬度", style="Muted.TLabel").pack(side=tk.LEFT)
        self.div_lat_var = tk.StringVar(value="—")
        ttk.Label(div_coord_row, textvariable=self.div_lat_var, style="Field.TLabel", width=14).pack(
            side=tk.LEFT, padx=(4, 0),
        )
        self.div_coord_hint = ttk.Label(self.time_frame, text="", style="Muted.TLabel")
        self.div_coord_hint.grid(row=7, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))

        self.use_true_solar_div_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.time_frame,
            text="时间起卦使用起卦地真太阳时",
            variable=self.use_true_solar_div_var,
        ).grid(row=8, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(8, 0))
        ttk.Label(
            self.time_frame,
            text="真太阳时仅校正经度；配合节气历换算时辰",
            style="Muted.TLabel",
        ).grid(row=9, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))

    def _build_number_section(self, parent: ttk.Frame) -> None:
        self.number_frame = ttk.LabelFrame(
            parent, text="  数字起卦（梅花报数）  ", style="Section.TLabelframe", padding=12
        )
        self.number_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            self.number_frame,
            text="上卦＝第一数 mod 8，下卦＝第二数 mod 8；"
            "两数时动爻＝(n1+n2) mod 6，三数时动爻＝第三数 mod 6（余 0 取 8/6）",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W)

        labels = ("第一数（上卦）", "第二数（下卦）", "第三数（动爻，可选）")
        self.number_n1_var = tk.StringVar(value="3")
        self.number_n2_var = tk.StringVar(value="8")
        self.number_n3_var = tk.StringVar(value="5")
        for col, (label, var) in enumerate(zip(labels, (
            self.number_n1_var, self.number_n2_var, self.number_n3_var,
        ))):
            ttk.Label(self.number_frame, text=label, style="Field.TLabel").grid(
                row=1, column=col, sticky=tk.W, padx=(0, 8), pady=(10, 4),
            )
            ttk.Entry(self.number_frame, textvariable=var, width=8).grid(
                row=2, column=col, sticky=tk.W, padx=(0, 8),
            )

    def _trigram_option(self, idx: int) -> str:
        if 1 <= idx <= 8:
            return TRIGRAM_SELECT_OPTIONS[idx - 1]
        return TRIGRAM_SELECT_OPTIONS[0]

    def _build_manual_section(self, parent: ttk.Frame) -> None:
        self.manual_frame = ttk.LabelFrame(
            parent, text="  手动选卦  ", style="Section.TLabelframe", padding=12
        )
        self.manual_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            self.manual_frame,
            text="选定上卦、下卦（乾1…坤8）；动爻可选，选「无」则为全静卦",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W)

        self.manual_upper_var = tk.StringVar(value=self._trigram_option(1))
        self.manual_lower_var = tk.StringVar(value=self._trigram_option(8))
        self.manual_changing_var = tk.StringVar(value=MANUAL_CHANGING_OPTIONS[0])

        fields = (
            ("上卦", self.manual_upper_var),
            ("下卦", self.manual_lower_var),
            ("动爻", self.manual_changing_var),
        )
        for col, (label, var) in enumerate(fields):
            ttk.Label(self.manual_frame, text=label, style="Field.TLabel").grid(
                row=1, column=col, sticky=tk.W, padx=(0, 10), pady=(10, 4),
            )
            values = TRIGRAM_SELECT_OPTIONS if col < 2 else MANUAL_CHANGING_OPTIONS
            combo = ttk.Combobox(
                self.manual_frame,
                textvariable=var,
                values=values,
                state="readonly",
                width=14,
            )
            combo.grid(row=2, column=col, sticky=tk.W, padx=(0, 10))
            combo.bind("<<ComboboxSelected>>", lambda _e: self._schedule_save())

    def _build_yarrow_section(self, parent: ttk.Frame) -> None:
        self.yarrow_frame = ttk.LabelFrame(
            parent, text="  蓍草法（大衍模拟）  ", style="Section.TLabelframe", padding=12
        )
        self.yarrow_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            self.yarrow_frame,
            text="五十蓍草取一，用四十九；每爻三变。程序模拟，非实体蓍草。",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self.yarrow_show_process_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.yarrow_frame,
            text="显示演卦过程",
            variable=self.yarrow_show_process_var,
            command=self._on_yarrow_show_process_changed,
        ).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        self.yarrow_process_frame = ttk.LabelFrame(
            self.yarrow_frame, text="  演卦过程  ", style="Section.TLabelframe", padding=8,
        )
        self.yarrow_process_text = tk.Text(
            self.yarrow_process_frame,
            height=10,
            width=48,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#faf8f5",
            fg="#3d3429",
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.yarrow_process_text.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            self.yarrow_process_frame,
            text="起卦后在此展示分二、挂一、揲四、归奇步骤",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(6, 0))

    def _build_character_section(self, parent: ttk.Frame) -> None:
        self.character_frame = ttk.LabelFrame(
            parent, text="  汉字起卦（梅花字课）  ", style="Section.TLabelframe", padding=12
        )
        self.character_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            self.character_frame,
            text="输入一字或一词；默认康熙字典笔画，未收录字以码点回退",
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W)

        ttk.Label(self.character_frame, text="汉字", style="Field.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=(10, 4),
        )
        self.character_input_var = tk.StringVar(value="问")
        char_entry = ttk.Entry(self.character_frame, textvariable=self.character_input_var, width=24)
        char_entry.grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        char_entry.bind("<KeyRelease>", lambda _e: self._refresh_character_preview())

        ttk.Label(self.character_frame, text="策略", style="Field.TLabel").grid(
            row=1, column=1, sticky=tk.W, pady=(10, 4),
        )
        self.character_strategy_var = tk.StringVar(value="auto")
        strategy_combo = ttk.Combobox(
            self.character_frame,
            textvariable=self.character_strategy_var,
            values=[f"{k} — {STRATEGY_LABELS[k]}" for k in CHARACTER_STRATEGIES],
            state="readonly",
            width=22,
        )
        strategy_combo.grid(row=2, column=1, sticky=tk.W, padx=(0, 10))
        strategy_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_character_strategy_changed())

        ttk.Label(self.character_frame, text="笔画口径", style="Field.TLabel").grid(
            row=1, column=2, sticky=tk.W, pady=(10, 4),
        )
        self.character_stroke_mode_var = tk.StringVar(value=STROKE_MODE_LABELS["kangxi"])
        stroke_combo = ttk.Combobox(
            self.character_frame,
            textvariable=self.character_stroke_mode_var,
            values=[STROKE_MODE_LABELS[m] for m in STROKE_MODES],
            state="readonly",
            width=14,
        )
        stroke_combo.grid(row=2, column=2, sticky=tk.W)
        stroke_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_character_preview())

        self.character_preview_var = tk.StringVar(value="")
        ttk.Label(
            self.character_frame,
            textvariable=self.character_preview_var,
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

    def _character_strategy_key(self) -> str:
        raw = self.character_strategy_var.get().split(" — ", 1)[0].strip()
        return raw if raw in CHARACTER_STRATEGIES else "auto"

    def _character_stroke_mode_key(self) -> str:
        label = self.character_stroke_mode_var.get()
        for key, name in STROKE_MODE_LABELS.items():
            if label == name:
                return key
        return "kangxi"

    def _on_character_strategy_changed(self) -> None:
        self._refresh_character_preview()
        self._schedule_save()

    def _refresh_character_preview(self) -> None:
        text = self.character_input_var.get().strip()
        if not text:
            self.character_preview_var.set("")
            return
        try:
            chars, strokes, sources = resolve_strokes(
                text,
                stroke_mode=self._character_stroke_mode_key(),
            )
            preview = format_stroke_preview(chars, strokes, sources, self._character_stroke_mode_key())
            self.character_preview_var.set(preview)
        except ValueError:
            self.character_preview_var.set("（请输入有效汉字）")

    def _collect_character_text(self) -> str | None:
        from bagua.character import parse_character_input

        return parse_character_input(self.character_input_var.get())

    def _on_yarrow_show_process_changed(self) -> None:
        if self.yarrow_show_process_var.get():
            self.yarrow_process_frame.grid(
                row=2, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0),
            )
        else:
            self.yarrow_process_frame.grid_forget()
        self._schedule_save()

    def _set_yarrow_process_text(self, content: str) -> None:
        self.yarrow_process_text.configure(state=tk.NORMAL)
        self.yarrow_process_text.delete("1.0", tk.END)
        if content:
            self.yarrow_process_text.insert(tk.END, content)
        self.yarrow_process_text.configure(state=tk.DISABLED)

    def _bind_autosave(self) -> None:
        for var in (
            self.question_var,
            self.bazi_var,
            self.birth_var,
            self.tz_display_var,
            self.div_tz_display_var,
            self.method_var,
            self.coin_mode_var,
            self.calendar_var,
            self.time_input_var,
        ):
            var.trace_add("write", lambda *_: self._schedule_save())
        self.birth_lon_var.trace_add("write", self._on_birth_lon_var_changed)
        self.div_lon_var.trace_add("write", self._on_div_lon_var_changed)
        self.birth_location_var.trace_add("write", self._on_birth_location_var_changed)
        self.div_location_var.trace_add("write", self._on_div_location_var_changed)
        self.use_now_var.trace_add("write", lambda *_: self._schedule_save())
        self.use_true_solar_birth_var.trace_add("write", lambda *_: self._schedule_save())
        self.use_true_solar_div_var.trace_add("write", lambda *_: self._schedule_save())
        self.yarrow_show_process_var.trace_add("write", lambda *_: self._schedule_save())
        for row in self._coin_vars:
            for var in row:
                var.trace_add("write", lambda *_: self._schedule_save())
        for var in (self.number_n1_var, self.number_n2_var, self.number_n3_var):
            var.trace_add("write", lambda *_: self._schedule_save())
        self.character_input_var.trace_add("write", lambda *_: self._schedule_save())
        self.tz_combo.bind("<<ComboboxSelected>>", lambda _e: self._schedule_save())
        self.div_tz_combo.bind("<<ComboboxSelected>>", lambda _e: self._schedule_save())

    def _current_birth_location(self) -> str:
        return self.birth_location_combo.get().strip() or self.birth_location_var.get().strip()

    def _current_div_location(self) -> str:
        return self.div_location_combo.get().strip() or self.div_location_var.get().strip()

    def _refresh_birth_coord_display(self) -> None:
        iana, _ = self._selected_birth_timezone()
        location = self._current_birth_location()
        lon, lat = resolve_display_coord(location, self.birth_lon_var.get(), iana)
        if location != LOCATION_CUSTOM:
            self.birth_lon_var.set(f"{lon:.2f}")
        self.birth_lat_var.set(format_latitude(lat))
        effective_lon = resolve_longitude(location, self.birth_lon_var.get(), iana)
        display_lon = effective_lon if effective_lon is not None else lon
        self.birth_coord_hint.configure(text=display_coord_hint(display_lon, iana, lat))

    def _refresh_div_coord_display(self) -> None:
        iana, _ = self._selected_divination_timezone()
        location = self._current_div_location()
        lon, lat = resolve_display_coord(location, self.div_lon_var.get(), iana)
        if location != LOCATION_CUSTOM:
            self.div_lon_var.set(f"{lon:.2f}")
        self.div_lat_var.set(format_latitude(lat))
        effective_lon = resolve_longitude(location, self.div_lon_var.get(), iana)
        display_lon = effective_lon if effective_lon is not None else lon
        self.div_coord_hint.configure(text=display_coord_hint(display_lon, iana, lat))

    def _on_birth_location_selected(self, _event: object | None = None) -> None:
        if self._loading_form:
            return
        self._sync_birth_location_ui()

    def _on_div_location_selected(self, _event: object | None = None) -> None:
        if self._loading_form:
            return
        self._sync_div_location_ui()

    def _on_birth_location_var_changed(self, *_args: object) -> None:
        if self._loading_form:
            return
        self._sync_birth_location_ui()

    def _on_div_location_var_changed(self, *_args: object) -> None:
        if self._loading_form:
            return
        self._sync_div_location_ui()

    def _on_birth_lon_var_changed(self, *_args: object) -> None:
        if self._loading_form:
            return
        if self._current_birth_location() == LOCATION_CUSTOM:
            self._refresh_birth_coord_display()
        self._schedule_save()

    def _on_div_lon_var_changed(self, *_args: object) -> None:
        if self._loading_form:
            return
        if self._current_div_location() == LOCATION_CUSTOM:
            self._refresh_div_coord_display()
        self._schedule_save()

    def _sync_birth_location_ui(self) -> None:
        location = self._current_birth_location()
        if location == LOCATION_CUSTOM:
            self.birth_lon_entry.configure(state="normal")
            if not self.birth_lon_var.get().strip():
                iana, _ = self._selected_birth_timezone()
                self.birth_lon_var.set(f"{default_longitude(iana):.2f}")
        else:
            self.birth_lon_entry.configure(state="readonly")
        self._refresh_birth_coord_display()
        if not self._loading_form:
            self._schedule_save()

    def _sync_div_location_ui(self) -> None:
        location = self._current_div_location()
        if location == LOCATION_CUSTOM:
            self.div_lon_entry.configure(state="normal")
            if not self.div_lon_var.get().strip():
                iana, _ = self._selected_divination_timezone()
                self.div_lon_var.set(f"{default_longitude(iana):.2f}")
        else:
            self.div_lon_entry.configure(state="readonly")
        self._refresh_div_coord_display()
        if not self._loading_form:
            self._schedule_save()

    def _on_birth_tz_changed(self) -> None:
        if self._current_birth_location() == LOCATION_FOLLOW_TZ:
            self._refresh_birth_coord_display()
        self._schedule_save()

    def _on_div_tz_changed(self) -> None:
        if self._current_div_location() == LOCATION_FOLLOW_TZ:
            self._refresh_div_coord_display()
        self._schedule_save()

    def _effective_birth_longitude(self) -> float | None:
        iana, _ = self._selected_birth_timezone()
        return resolve_longitude(
            self._current_birth_location(),
            self.birth_lon_var.get(),
            iana,
        )

    def _effective_divination_longitude(self) -> float | None:
        iana, _ = self._selected_divination_timezone()
        return resolve_longitude(
            self._current_div_location(),
            self.div_lon_var.get(),
            iana,
        )

    def _validate_location_fields(self) -> str | None:
        if self._current_birth_location() == LOCATION_CUSTOM:
            if parse_longitude(self.birth_lon_var.get()) is None:
                return "出生经度格式无效，请填写数字（东经为正，西经为负）"
        if self._current_div_location() == LOCATION_CUSTOM:
            if parse_longitude(self.div_lon_var.get()) is None:
                return "起卦经度格式无效，请填写数字（东经为正，西经为负）"
        return None

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

    def _update_coin_mode_visibility(self) -> None:
        if self.method_var.get() == "coin":
            self.coin_mode_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        else:
            self.coin_mode_frame.grid_forget()

    def _on_method_changed(self) -> None:
        method = self.method_var.get()
        self._update_coin_mode_visibility()
        self.coin_frame.pack_forget()
        self.time_frame.pack_forget()
        self.number_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.yarrow_frame.pack_forget()
        self.character_frame.pack_forget()
        if method == "coin":
            self.coin_frame.pack(fill=tk.X, pady=(0, 4))
            self._on_coin_mode_changed()
        elif method == "time":
            self.time_frame.pack(fill=tk.X, pady=(0, 4))
        elif method == "number":
            self.number_frame.pack(fill=tk.X, pady=(0, 4))
        elif method == "manual":
            self.manual_frame.pack(fill=tk.X, pady=(0, 4))
        elif method == "yarrow":
            self.yarrow_frame.pack(fill=tk.X, pady=(0, 4))
            self._on_yarrow_show_process_changed()
        elif method == "character":
            self.character_frame.pack(fill=tk.X, pady=(0, 4))
            self._refresh_character_preview()
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
        iana, region = self._selected_birth_timezone()
        tz = get_timezone(iana, region)
        computed, _note = compute_bazi(
            birth,
            tz,
            longitude=self._effective_birth_longitude(),
            use_true_solar=self.use_true_solar_birth_var.get(),
        )
        if not computed:
            messagebox.showwarning("排盘失败", "无法解析出生时间，请检查格式与时区")
            return
        self.bazi_var.set(computed)
        self.status_var.set("已自动排八字")

    def _timezone_from_label(self, label: str, fallback_iana: str, fallback_label: str) -> tuple[str, str]:
        for iana, preset_label in TIMEZONE_PRESETS:
            if preset_label == label:
                return iana, preset_label
        return fallback_iana, fallback_label

    def _selected_birth_timezone(self) -> tuple[str, str]:
        return self._timezone_from_label(
            self.tz_display_var.get(),
            self._config.timezone,
            self._config.region_label,
        )

    def _selected_divination_timezone(self) -> tuple[str, str]:
        return self._timezone_from_label(
            self.div_tz_display_var.get(),
            self._config.divination_timezone or self._config.timezone,
            self._config.divination_region_label or self._config.region_label,
        )

    def _collect_coin_tosses_state(self) -> list[list[str]]:
        return [[v.get() for v in row] for row in self._coin_vars]

    def _build_context(self) -> UserContext:
        birth_iana, birth_region = self._selected_birth_timezone()
        div_iana, div_region = self._selected_divination_timezone()
        return UserContext(
            question=self.question_var.get().strip(),
            bazi=self.bazi_var.get().strip(),
            birth_datetime=self.birth_var.get().strip(),
            birth_tz=get_timezone(birth_iana, birth_region),
            divination_tz=get_timezone(div_iana, div_region),
            coin_mode=self.coin_mode_var.get(),
            calendar_mode=self.calendar_var.get(),
            include_hexagram_texts=self._config.include_hexagram_texts,
            birth_longitude=self._effective_birth_longitude(),
            divination_longitude=self._effective_divination_longitude(),
            use_true_solar_birth=self.use_true_solar_birth_var.get(),
            use_true_solar_divination=self.use_true_solar_div_var.get(),
        )

    def _collect_manual_selection(self) -> tuple[int, int, int | None] | None:
        upper = parse_trigram_index(self.manual_upper_var.get())
        lower = parse_trigram_index(self.manual_lower_var.get())
        if upper is None or lower is None:
            return None
        changing = parse_manual_changing(self.manual_changing_var.get())
        return upper, lower, changing

    def _load_manual_from_config(self, cfg: UserConfig) -> None:
        upper = cfg.manual_upper if 1 <= cfg.manual_upper <= 8 else 1
        lower = cfg.manual_lower if 1 <= cfg.manual_lower <= 8 else 8
        self.manual_upper_var.set(self._trigram_option(upper))
        self.manual_lower_var.set(self._trigram_option(lower))
        if cfg.manual_changing and 1 <= cfg.manual_changing <= 6:
            self.manual_changing_var.set(MANUAL_CHANGING_OPTIONS[cfg.manual_changing])
        else:
            self.manual_changing_var.set(MANUAL_CHANGING_OPTIONS[0])

    def _manual_state_from_form(self) -> tuple[int, int, int]:
        sel = self._collect_manual_selection()
        if sel is None:
            return 1, 8, 0
        upper, lower, changing = sel
        return upper, lower, 0 if changing is None else changing

    def _collect_number_inputs(self) -> list[int] | None:
        parts = [
            self.number_n1_var.get().strip(),
            self.number_n2_var.get().strip(),
            self.number_n3_var.get().strip(),
        ]
        if not parts[0] or not parts[1]:
            return None
        raw = " ".join(p for p in parts if p)
        return parse_number_input(raw)

    def _load_number_inputs_from_config(self, cfg: UserConfig) -> None:
        stored = cfg.number_inputs or ["3", "8", "5"]
        values = (stored + ["", "", ""])[:3]
        self.number_n1_var.set(values[0] or "3")
        self.number_n2_var.set(values[1] or "8")
        self.number_n3_var.set(values[2])

    def _collect_number_inputs_state(self) -> list[str]:
        return [
            self.number_n1_var.get().strip(),
            self.number_n2_var.get().strip(),
            self.number_n3_var.get().strip(),
        ]

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
            valid_methods = ("coin", "time", "random", "number", "manual", "yarrow", "character")
            self.method_var.set(cfg.last_method if cfg.last_method in valid_methods else "coin")
            self.use_now_var.set(cfg.use_current_time)
            self.time_input_var.set(cfg.time_input)
            self._load_coin_tosses_from_config(cfg)
            self._load_number_inputs_from_config(cfg)
            self._load_manual_from_config(cfg)
            self.yarrow_show_process_var.set(cfg.yarrow_show_process)
            self.character_input_var.set(cfg.character_input or "问")
            strategy = cfg.character_strategy if cfg.character_strategy in CHARACTER_STRATEGIES else "auto"
            self.character_strategy_var.set(f"{strategy} — {STRATEGY_LABELS[strategy]}")
            stroke_key = cfg.character_stroke_mode if cfg.character_stroke_mode in STROKE_MODES else "kangxi"
            self.character_stroke_mode_var.set(STROKE_MODE_LABELS[stroke_key])

            labels = [label for _, label in TIMEZONE_PRESETS]
            if cfg.region_label in labels:
                self.tz_display_var.set(cfg.region_label)
            else:
                self.tz_display_var.set(TIMEZONE_PRESETS[0][1])

            div_label = cfg.divination_region_label or cfg.region_label
            if div_label in labels:
                self.div_tz_display_var.set(div_label)
            else:
                self.div_tz_display_var.set(TIMEZONE_PRESETS[0][1])

            birth_loc = cfg.birth_location or infer_location_label(
                cfg.birth_longitude, cfg.timezone,
            )
            if birth_loc not in LOCATION_OPTIONS:
                birth_loc = default_city_for_timezone(cfg.timezone)
            self.birth_location_var.set(birth_loc)
            if birth_loc == LOCATION_CUSTOM and cfg.birth_longitude is not None:
                self.birth_lon_var.set(f"{cfg.birth_longitude:.2f}")

            div_iana = cfg.divination_timezone or cfg.timezone
            div_loc = cfg.divination_location or infer_location_label(
                cfg.divination_longitude, div_iana,
            )
            if div_loc not in LOCATION_OPTIONS:
                div_loc = default_city_for_timezone(div_iana)
            self.div_location_var.set(div_loc)
            if div_loc == LOCATION_CUSTOM and cfg.divination_longitude is not None:
                self.div_lon_var.set(f"{cfg.divination_longitude:.2f}")

            self.use_true_solar_birth_var.set(cfg.use_true_solar_birth)
            self.use_true_solar_div_var.set(cfg.use_true_solar_divination)
            self._sync_birth_location_ui()
            self._sync_div_location_ui()

            self._on_method_changed()
            self._on_use_now_changed()
            self._on_calendar_changed()
        finally:
            self._loading_form = False

    def _persist_config_from_form(self) -> None:
        birth_iana, birth_region = self._selected_birth_timezone()
        div_iana, div_region = self._selected_divination_timezone()
        manual_upper, manual_lower, manual_changing = self._manual_state_from_form()
        self._config = UserConfig(
            timezone=birth_iana,
            region_label=birth_region,
            divination_timezone=div_iana,
            divination_region_label=div_region,
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
            number_inputs=self._collect_number_inputs_state(),
            manual_upper=manual_upper,
            manual_lower=manual_lower,
            manual_changing=manual_changing,
            yarrow_show_process=self.yarrow_show_process_var.get(),
            character_input=self.character_input_var.get().strip(),
            character_strategy=self._character_strategy_key(),
            character_stroke_mode=self._character_stroke_mode_key(),
            birth_location=self._current_birth_location(),
            divination_location=self._current_div_location(),
            birth_longitude=self._effective_birth_longitude(),
            divination_longitude=self._effective_divination_longitude(),
            use_true_solar_birth=self.use_true_solar_birth_var.get(),
            use_true_solar_divination=self.use_true_solar_div_var.get(),
        )
        save_config(self._config)
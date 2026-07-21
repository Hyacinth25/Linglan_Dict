import tkinter as tk
from tkinter import ttk


def build_competition_page(app):
    mix = app.mix_color
    RoundedTag = app.RoundedTag
    app.competition_page = tk.Frame(app.root, bg=app.bg_color, padx=34, pady=20)

    header_row = tk.Frame(app.competition_page, bg=app.bg_color)
    header_row.pack(fill="x")
    app.competition_back_button = ttk.Button(header_row, text="← 返回", command=app._back_to_main)
    app.competition_back_button.pack(side="left")
    app.competition_title = RoundedTag(
        header_row,
        text="单词组竞赛",
        text_font=(app.cn_font_family, 18, "bold"),
        bg=app.bg_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=16,
        padx=20,
        pady=8,
    )
    app.competition_title.pack(side="left", padx=(18, 0))
    app.competition_today_label = tk.Label(
        header_row,
        textvariable=app.competition_today_total_var,
        bg=app.bg_color,
        fg=app.config.theme_color,
        font=(app.cn_font_family, 18, "bold"),
    )
    app.competition_today_label.pack(side="left", padx=(20, 0))
    app.competition_review_label = tk.Label(
        header_row,
        textvariable=app.competition_review_var,
        bg=app.bg_color,
        fg=app.config.theme_color,
        font=(app.cn_font_family, 16, "bold"),
    )
    app.competition_review_label.pack(side="left", padx=(12, 0))
    app.competition_history_button = ttk.Button(
        header_row,
        text="查看历史",
        command=app._show_competition_history_popup,
    )
    app.competition_history_button.pack(side="right", padx=(0, 6))
    app.competition_export_button = ttk.Button(
        header_row,
        text="一键导出 Excel",
        command=app._export_competition_excel,
    )
    app.competition_export_button.pack(side="right")

    control_panel = tk.Frame(app.competition_page, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=14)
    control_panel.pack(fill="x", pady=(14, 10))
    app.competition_control_tag = RoundedTag(
        control_panel,
        text="竞赛设置",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=16,
        pady=7,
    )
    app.competition_control_tag.pack(anchor="w")
    control_row = tk.Frame(control_panel, bg=app.card_color)
    control_row.pack(fill="x", pady=(10, 0))

    app.competition_count_label = tk.Label(
        control_row,
        text="单词组数量",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
    )
    app.competition_count_label.pack(side="left")
    app.competition_count_combo = ttk.Combobox(
        control_row,
        textvariable=app.competition_group_count_var,
        values=("1", "5", "10", "25", "50"),
        state="readonly",
        width=6,
    )
    app.competition_count_combo.pack(side="left", padx=(8, 18))
    app.competition_count_combo.bind("<<ComboboxSelected>>", app._on_competition_count_change)

    app.competition_start_label = tk.Label(
        control_row,
        text="开始单词组编号 (1-100)",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
    )
    app.competition_start_label.pack(side="left")
    app.competition_start_spinbox = tk.Spinbox(
        control_row,
        from_=1,
        to=100,
        textvariable=app.competition_start_group_var,
        width=6,
        font=(app.en_font_family, 10),
        command=app._on_competition_start_change,
    )
    app.competition_start_spinbox.pack(side="left", padx=(8, 18))
    app.competition_start_spinbox.bind("<FocusOut>", lambda _e: app._on_competition_start_change())
    app.competition_start_spinbox.bind("<Return>", lambda _e: app._on_competition_start_change())

    app.competition_range_label = tk.Label(
        control_row,
        textvariable=app.competition_range_var,
        bg=app.card_color,
        fg=app.text_color,
        font=(app.cn_font_family, 10, "bold"),
    )
    app.competition_range_label.pack(side="left")

    body_panel = tk.Frame(app.competition_page, bg=app.bg_color)
    body_panel.pack(fill="both", expand=True, pady=(0, 8))
    body_panel.grid_columnconfigure(0, weight=3)
    body_panel.grid_columnconfigure(1, weight=2)
    body_panel.grid_rowconfigure(0, weight=1)

    history_panel = tk.Frame(body_panel, bg=app.card_color, highlightthickness=0, bd=0, padx=16, pady=14)
    history_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

    history_header_row = tk.Frame(history_panel, bg=app.card_color)
    history_header_row.pack(fill="x", pady=(0, 8))

    app.competition_history_tag = RoundedTag(
        history_header_row,
        text="历史竞赛记录",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=14,
        pady=6,
    )
    app.competition_history_tag.pack(side="left")

    app.competition_filter_var = tk.BooleanVar(value=False)
    app.competition_filter_check = tk.Checkbutton(
        history_header_row,
        text="仅查看本组别成绩",
        variable=app.competition_filter_var,
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        selectcolor=app.card_color,
        activebackground=app.card_color,
        activeforeground=app.text_secondary,
        command=app._on_competition_filter_toggle,
    )
    app.competition_filter_check.pack(side="right")

    app.competition_highlight_check = tk.Checkbutton(
        history_header_row,
        text="同组成绩高亮",
        variable=app.competition_highlight_same_group_var,
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        selectcolor=app.card_color,
        activebackground=app.card_color,
        activeforeground=app.text_secondary,
        command=app._on_competition_filter_toggle,
    )
    app.competition_highlight_check.pack(side="right", padx=(0, 8))

    app.competition_today_only_check = tk.Checkbutton(
        history_header_row,
        text="仅查看今日成绩",
        variable=app.competition_today_only_var,
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        selectcolor=app.card_color,
        activebackground=app.card_color,
        activeforeground=app.text_secondary,
        command=app._on_competition_filter_toggle,
    )
    app.competition_today_only_check.pack(side="right", padx=(0, 8))

    app.competition_group_count_filter_var = tk.BooleanVar(value=False)
    app.competition_group_count_filter_check = tk.Checkbutton(
        history_header_row,
        text="仅显示同单词组数量成绩",
        variable=app.competition_group_count_filter_var,
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        selectcolor=app.card_color,
        activebackground=app.card_color,
        activeforeground=app.text_secondary,
        command=app._on_competition_filter_toggle,
    )
    app.competition_group_count_filter_check.pack(side="right", padx=(0, 8))

    tree_container = tk.Frame(history_panel, bg=app.card_color)
    tree_container.pack(fill="both", expand=True)
    columns = ("list_range", "elapsed", "rank", "total_rank", "date", "grade", "remark")
    app.competition_history_tree = ttk.Treeview(
        tree_container,
        columns=columns,
        show="headings",
        height=14,
    )
    headings = {
        "list_range": "单词组",
        "elapsed": "用时",
        "rank": "排名",
        "total_rank": "总榜排名",
        "date": "时间",
        "grade": "等级",
        "remark": "备注",
    }
    widths = {
        "list_range": 100,
        "elapsed": 90,
        "rank": 55,
        "total_rank": 65,
        "date": 90,
        "grade": 50,
        "remark": 55,
    }
    for column in columns:
        app.competition_history_tree.heading(column, text=headings[column])
        app.competition_history_tree.column(
            column,
            width=widths[column],
            anchor="center",
            stretch=True,
        )
    history_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=app.competition_history_tree.yview)
    app.competition_history_tree.configure(yscrollcommand=history_scroll.set)
    app.competition_history_tree.pack(side="left", fill="both", expand=True)
    history_scroll.pack(side="left", fill="y")
    app.competition_history_tree.bind("<Button-3>", app._on_competition_history_right_click)
    app.competition_history_tree.bind("<Double-1>", app._on_competition_history_double_click)

    app.competition_history_menu = tk.Menu(app.root, tearoff=0)
    app.competition_history_menu.add_command(label="删除此记录", command=app._delete_selected_competition_record)

    current_panel = tk.Frame(body_panel, bg=app.card_color, highlightthickness=0, bd=0, padx=18, pady=16)
    current_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    app.competition_current_tag = RoundedTag(
        current_panel,
        text="当前竞赛",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=14,
        pady=6,
    )
    app.competition_current_tag.pack(anchor="w", pady=(0, 8))

    hint_label = tk.Label(
        current_panel,
        textvariable=app.competition_hint_var,
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        wraplength=280,
        justify="left",
        anchor="w",
    )
    hint_label.pack(fill="x", pady=(0, 10))
    app.competition_hint_label = hint_label

    stopwatch_label = tk.Label(
        current_panel,
        textvariable=app.competition_stopwatch_var,
        bg=app.card_color,
        fg=app.config.theme_color,
        font=(app.en_font_family, 34, "bold"),
    )
    stopwatch_label.pack(pady=(6, 10))
    app.competition_stopwatch_label = stopwatch_label

    result_frame = tk.Frame(current_panel, bg=app.card_color)
    result_frame.pack(fill="x", pady=(4, 8))
    app.competition_result_frame = result_frame
    app.competition_result_labels = {}
    for key, caption in (
        ("list_range", "单词组"),
        ("elapsed", "用时"),
        ("rank", "组别排名"),
        ("total_rank", "总榜排名"),
        ("date", "时间"),
        ("grade", "等级"),
        ("remark", "备注"),
    ):
        row = tk.Frame(result_frame, bg=app.card_color)
        row.pack(fill="x", pady=1)
        tk.Label(
            row,
            text=caption,
            bg=app.card_color,
            fg=app.text_secondary,
            font=(app.cn_font_family, 11),
            width=8,
            anchor="w",
        ).pack(side="left")
        value_label = tk.Label(
            row,
            text="-",
            bg=app.card_color,
            fg=app.text_color,
            font=(app.cn_font_family, 12, "bold"),
            anchor="w",
        )
        value_label.pack(side="left", fill="x", expand=True, padx=(8, 0))
        app.competition_result_labels[key] = value_label

    invalid_row = tk.Frame(current_panel, bg=app.card_color)
    invalid_row.pack(fill="x", side="bottom", pady=(10, 0))
    app.competition_invalid_button = ttk.Button(
        invalid_row,
        text="成绩无效",
        command=app._invalidate_last_competition,
        state="disabled",
    )
    app.competition_invalid_button.pack(side="right")

    app.competition_status_label = tk.Label(
        app.competition_page,
        textvariable=app.competition_status_var,
        bg=app.bg_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        anchor="w",
    )
    app.competition_status_label.pack(fill="x", pady=(4, 0))

    app.competition_page_panels = [control_panel, history_panel, current_panel]
    app.competition_page_tags = [
        app.competition_title,
        app.competition_control_tag,
        app.competition_history_tag,
        app.competition_current_tag,
    ]
    app.competition_page_checkbuttons = [
        app.competition_filter_check,
        app.competition_group_count_filter_check,
        app.competition_highlight_check,
        app.competition_today_only_check,
    ]

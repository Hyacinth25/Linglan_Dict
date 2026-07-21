import tkinter as tk
from tkinter import ttk


def build_home_page(app):
    mix = app.mix_color
    RoundedTag = app.RoundedTag
    app.container = tk.Frame(app.root, bg=app.bg_color, padx=34, pady=28)
    app.container.pack(fill="both", expand=True)
    app.title_tag = RoundedTag(app.container, text="铃兰词典", text_font=(app.cn_font_family, 24, "bold"), bg=app.bg_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.85), outline=app.config.theme_color, radius=22, padx=34, pady=12)
    app.title_tag.pack(anchor="center", pady=(0, 16))
    app.separator_label = tk.Label(app.container, bg=app.bg_color, bd=0)
    app.separator_label.pack(anchor="center", pady=(0, 14))
    app.icons_panel = tk.Frame(app.container, bg=app.bg_color)
    app.icons_panel.pack(fill="x", pady=(0, 20))
    app.icons_row = tk.Frame(app.icons_panel, bg=app.bg_color)
    app.icons_row.pack(anchor="center")
    app._build_icons()
    app.search_panel = tk.Frame(app.container, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    app.search_panel.pack(fill="both", expand=True)
    app.search_tag = RoundedTag(app.search_panel, text="查找单词", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.86), outline=app.config.theme_color, radius=14, padx=18, pady=7)
    app.search_tag.pack(anchor="w")
    search_row = tk.Frame(app.search_panel, bg=app.card_color)
    search_row.pack(fill="x", pady=(12, 10))
    app.search_entry = ttk.Entry(search_row, textvariable=app.search_word_var, font=(app.en_font_family, 11))
    app.search_entry.pack(side="left", fill="x", expand=True, ipady=4)
    app.search_entry.bind("<Return>", app._on_search_enter)
    app.search_button = ttk.Button(search_row, text="🔎", command=app._search_word, width=3)
    app.search_button.pack(side="left", padx=(8, 0))
    app.lookup_full_button = ttk.Button(search_row, text="⛶", command=app._open_lookup_page, width=3)
    app.lookup_full_button.pack(side="left", padx=(8, 0))
    app.result_text = tk.Text(app.search_panel, height=7, wrap="word", relief="flat", bd=0, padx=12, pady=10, bg=mix(app.config.theme_color, "#ffffff", 0.93), fg=app.text_color, font=(app.en_font_family, 11))
    app.result_text.pack(fill="both", expand=True)
    app.result_text.configure(state="disabled")
    app.transition_overlay = tk.Frame(app.root, bg=mix(app.config.theme_color, "#ffffff", 0.65))
    app.transition_label = tk.Label(app.transition_overlay, text="铃兰在整理书页...", bg=mix(app.config.theme_color, "#ffffff", 0.65), fg=app.config.theme_color, font=(app.cn_font_family, 13, "bold"))
    app.transition_label.pack(pady=(220, 10))
    app.transition_tip_var = tk.StringVar(value="")
    app.transition_tip_label = tk.Label(
        app.transition_overlay,
        textvariable=app.transition_tip_var,
        bg=mix(app.config.theme_color, "#ffffff", 0.65),
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
        anchor="w",
        justify="left",
        wraplength=620,
    )
    app.transition_tip_label.place(relx=0.02, rely=0.98, anchor="sw")
    app.transition_bar = ttk.Progressbar(app.transition_overlay, orient="horizontal", mode="determinate", maximum=100, length=280)
    app.transition_bar.pack()


def build_lookup_page(app):
    mix = app.mix_color
    RoundedTag = app.RoundedTag
    app.lookup_page = tk.Frame(app.root, bg=app.bg_color, padx=34, pady=28)

    header_row = tk.Frame(app.lookup_page, bg=app.bg_color)
    header_row.pack(fill="x")
    app.lookup_back_button = ttk.Button(header_row, text="← 返回", command=app._back_to_main)
    app.lookup_back_button.pack(side="left")
    app.lookup_title = RoundedTag(
        header_row,
        text="全屏查词",
        text_font=(app.cn_font_family, 18, "bold"),
        bg=app.bg_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=16,
        padx=20,
        pady=8,
    )
    app.lookup_title.pack(side="left", padx=(18, 0))
    app.lookup_stats_label = tk.Label(
        header_row,
        textvariable=app.lookup_stats_var,
        bg=app.bg_color,
        fg=app.config.theme_color,
        font=(app.cn_font_family, 14, "bold"),
    )
    app.lookup_stats_label.pack(side="right")

    search_panel = tk.Frame(app.lookup_page, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    search_panel.pack(fill="x", pady=(16, 12))
    app.lookup_search_tag = RoundedTag(
        search_panel,
        text="查词输入",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=16,
        pady=7,
    )
    app.lookup_search_tag.pack(anchor="w")

    lookup_row = tk.Frame(search_panel, bg=app.card_color)
    lookup_row.pack(fill="x", pady=(10, 0))
    app.lookup_entry = ttk.Entry(lookup_row, textvariable=app.lookup_word_var, font=(app.en_font_family, 14))
    app.lookup_entry.pack(side="left", fill="x", expand=True, ipady=6)
    app.lookup_entry.bind("<Return>", app._on_lookup_enter)
    app.lookup_search_button = ttk.Button(lookup_row, text="查词", command=app._search_lookup_page)
    app.lookup_search_button.pack(side="left", padx=(8, 0))
    app.lookup_play_button = ttk.Button(lookup_row, text="🔊", command=app._play_current_lookup_pronunciation, width=3)
    app.lookup_play_button.pack(side="left", padx=(8, 0))
    app.lookup_clear_button = ttk.Button(lookup_row, text="清空", command=app._clear_lookup_entry)
    app.lookup_clear_button.pack(side="left", padx=(8, 0))

    body_panel = tk.Frame(app.lookup_page, bg=app.bg_color)
    body_panel.pack(fill="both", expand=True)
    body_panel.grid_columnconfigure(0, weight=1, uniform="lookup_columns")
    body_panel.grid_columnconfigure(1, weight=1, uniform="lookup_columns")
    body_panel.grid_rowconfigure(0, weight=1)

    result_panel = tk.Frame(body_panel, bg=app.card_color, padx=20, pady=16)
    result_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    app.lookup_result_tag = RoundedTag(
        result_panel,
        text="查询结果",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=16,
        pady=7,
    )
    app.lookup_result_tag.pack(anchor="w")
    app.lookup_result_text = tk.Text(
        result_panel,
        wrap="word",
        width=1,
        relief="flat",
        bd=0,
        padx=14,
        pady=12,
        bg=mix(app.config.theme_color, app.surface_mix_base, app.result_mix_ratio),
        fg=app.text_color,
        font=(app.en_font_family, 13),
    )
    app.lookup_result_text.pack(fill="both", expand=True, pady=(10, 0))
    app.lookup_result_text.configure(state="disabled")

    history_panel = tk.Frame(body_panel, bg=app.card_color, padx=14, pady=16)
    history_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    app.lookup_history_tag = RoundedTag(
        history_panel,
        text="历史查询",
        text_font=(app.cn_font_family, 12, "bold"),
        bg=app.card_color,
        fg=app.config.theme_color,
        fill=mix(app.config.theme_color, app.tag_mix_base, app.tag_fill_ratio),
        outline=app.config.theme_color,
        radius=14,
        padx=14,
        pady=7,
    )
    app.lookup_history_tag.pack(anchor="w")
    app.lookup_history_listbox = tk.Listbox(
        history_panel,
        width=1,
        relief="flat",
        bd=0,
        font=(app.cn_font_family, 10),
        activestyle="none",
    )
    app.lookup_history_listbox.pack(fill="both", expand=True, pady=(10, 0))
    app.lookup_history_listbox.bind("<Double-Button-1>", app._open_lookup_history_item)

    app.lookup_page_panels = [search_panel, result_panel, history_panel]
    app.lookup_page_tags = [
        app.lookup_title,
        app.lookup_search_tag,
        app.lookup_result_tag,
        app.lookup_history_tag,
    ]

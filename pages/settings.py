import tkinter as tk
from tkinter import ttk


def build_settings_page(app):
    mix = app.mix_color
    RoundedTag = app.RoundedTag
    app.settings_page = tk.Frame(app.root, bg=app.bg_color, padx=34, pady=28)

    app.settings_scroll_container = tk.Frame(app.settings_page, bg=app.bg_color)
    app.settings_scroll_container.pack(fill="both", expand=True)
    app.settings_scroll_canvas = tk.Canvas(
        app.settings_scroll_container,
        bg=app.bg_color,
        highlightthickness=0,
        bd=0,
    )
    app.settings_scroll_canvas.pack(fill="both", expand=True)
    app.settings_content = tk.Frame(app.settings_scroll_canvas, bg=app.bg_color)
    app.settings_canvas_window = app.settings_scroll_canvas.create_window(
        (0, 0),
        window=app.settings_content,
        anchor="nw",
    )

    def _on_settings_content_configure(_event=None):
        app.settings_scroll_canvas.configure(scrollregion=app.settings_scroll_canvas.bbox("all"))

    def _on_settings_canvas_configure(event):
        app.settings_scroll_canvas.itemconfigure(app.settings_canvas_window, width=event.width)

    def _on_settings_mousewheel(event):
        if hasattr(event, "delta") and event.delta:
            app.settings_scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            app.settings_scroll_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            app.settings_scroll_canvas.yview_scroll(1, "units")
        return "break"

    def _bind_settings_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_settings_mousewheel, add="+")
        widget.bind("<Button-4>", _on_settings_mousewheel, add="+")
        widget.bind("<Button-5>", _on_settings_mousewheel, add="+")
        for child in widget.winfo_children():
            _bind_settings_mousewheel(child)

    app.settings_content.bind("<Configure>", _on_settings_content_configure)
    app.settings_scroll_canvas.bind("<Configure>", _on_settings_canvas_configure)

    header_row = tk.Frame(app.settings_content, bg=app.bg_color)
    header_row.pack(fill="x")
    app.settings_back_button = ttk.Button(header_row, text="← 返回", command=app._back_to_main)
    app.settings_back_button.pack(side="left")
    app.settings_title = RoundedTag(header_row, text="设置功能", text_font=(app.cn_font_family, 18, "bold"), bg=app.bg_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.86), outline=app.config.theme_color, radius=16, padx=20, pady=8)
    app.settings_title.pack(side="left", padx=(18, 0))

    color_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    color_panel.pack(fill="x", pady=(16, 12))
    app.settings_theme_tag = RoundedTag(color_panel, text="主题色设置", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_theme_tag.pack(anchor="w")
    color_row = tk.Frame(color_panel, bg=app.card_color)
    color_row.pack(fill="x", pady=(10, 0))
    app.color_block = tk.Label(color_row, width=3, height=1, relief="flat", bd=0, bg=app.config.theme_color, highlightthickness=1)
    app.color_block.pack(side="left")
    app.theme_color_text = tk.Label(color_row, textvariable=app.theme_var, font=(app.cn_font_family, 10), bg=app.card_color, fg=app.text_secondary)
    app.theme_color_text.pack(side="left", padx=(10, 14))
    app.color_button = ttk.Button(color_row, text="更换", command=app._choose_theme_color)
    app.color_button.pack(side="left")
    preset_row = tk.Frame(color_panel, bg=app.card_color)
    preset_row.pack(fill="x", pady=(10, 0))
    ttk.Button(preset_row, text="深棕色", command=lambda: app._set_theme_color("#6f4e37")).pack(side="left")
    ttk.Button(preset_row, text="淡绿色", command=lambda: app._set_theme_color("#7eaf8f")).pack(side="left", padx=(8, 0))
    ttk.Button(preset_row, text="柔和粉色", command=lambda: app._set_theme_color("#d596a7")).pack(side="left", padx=(8, 0))
    mode_row = tk.Frame(color_panel, bg=app.card_color)
    mode_row.pack(fill="x", pady=(10, 0))
    app.mode_text = tk.Label(mode_row, textvariable=app.mode_var, font=(app.cn_font_family, 10), bg=app.card_color, fg=app.text_secondary)
    app.mode_text.pack(side="left")
    app.day_mode_button = ttk.Button(mode_row, text="日间模式", command=lambda: app._set_theme_mode("day"))
    app.day_mode_button.pack(side="left", padx=(10, 0))
    app.night_mode_button = ttk.Button(mode_row, text="夜间模式", command=lambda: app._set_theme_mode("night"))
    app.night_mode_button.pack(side="left", padx=(8, 0))

    font_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    font_panel.pack(fill="x", pady=(0, 12))
    app.settings_font_tag = RoundedTag(font_panel, text="字体设置（中文/英文）", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_font_tag.pack(anchor="w")
    font_row = tk.Frame(font_panel, bg=app.card_color)
    font_row.pack(fill="x", pady=(10, 0))
    app.settings_cn_font_label = tk.Label(font_row, text="中文", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.settings_cn_font_label.pack(side="left")
    app.cn_font_combo = ttk.Combobox(font_row, textvariable=app.cn_font_var, values=app._font_options(app.CN_COMMON_FONTS), state="readonly", width=14)
    app.cn_font_combo.pack(side="left", padx=(8, 14))
    app.cn_font_combo.bind("<<ComboboxSelected>>", app._on_cn_font_change)
    app.settings_en_font_label = tk.Label(font_row, text="英文", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.settings_en_font_label.pack(side="left")
    app.en_font_combo = ttk.Combobox(font_row, textvariable=app.en_font_var, values=app._font_options(app.EN_COMMON_FONTS), state="readonly", width=14)
    app.en_font_combo.pack(side="left", padx=(8, 14))
    app.en_font_combo.bind("<<ComboboxSelected>>", app._on_en_font_change)
    app.settings_size_label = tk.Label(font_row, text="大小", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.settings_size_label.pack(side="left")
    app.font_size_combo = ttk.Combobox(font_row, textvariable=app.font_size_var, values=("normal", "large", "xlarge"), state="readonly", width=12)
    app.font_size_combo.pack(side="left", padx=(8, 0))
    app.font_size_combo.bind("<<ComboboxSelected>>", app._on_font_size_change)

    api_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    api_panel.pack(fill="x", pady=(0, 12))
    app.settings_api_tag = RoundedTag(api_panel, text="API Key设置", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_api_tag.pack(anchor="w")
    api_row = tk.Frame(api_panel, bg=app.card_color)
    api_row.pack(fill="x", pady=(10, 0))
    app.api_key_entry = ttk.Entry(api_row, textvariable=app.api_key_var, show="*")
    app.api_key_entry.pack(side="left", fill="x", expand=True, ipady=4)
    app.api_key_save_button = ttk.Button(api_row, text="保存到.env", command=app._save_env_vars)
    app.api_key_save_button.pack(side="left", padx=(8, 0))
    base_row = tk.Frame(api_panel, bg=app.card_color)
    base_row.pack(fill="x", pady=(8, 0))
    app.base_url_entry = ttk.Entry(base_row, textvariable=app.base_url_var)
    app.base_url_entry.pack(side="left", fill="x", expand=True, ipady=4)
    app.env_reload_button = ttk.Button(base_row, text="重新加载", command=app._reload_env_vars)
    app.env_reload_button.pack(side="left", padx=(8, 0))

    account_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    account_panel.pack(fill="x", pady=(0, 12))
    app.settings_account_tag = RoundedTag(account_panel, text="账号数据", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_account_tag.pack(anchor="w")
    account_row = tk.Frame(account_panel, bg=app.card_color)
    account_row.pack(fill="x", pady=(10, 0))
    app.account_hint_label = tk.Label(account_row, text="导入/导出包含设置、个人词库与学习记录", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.account_hint_label.pack(side="left")
    tk.Frame(account_row, bg=app.card_color).pack(side="left", fill="x", expand=True)
    app.account_import_button = ttk.Button(account_row, text="导入账号文件", command=app._import_account_data)
    app.account_import_button.pack(side="left", padx=(8, 0))
    app.account_export_button = ttk.Button(account_row, text="导出账号文件", command=app._export_account_data)
    app.account_export_button.pack(side="left", padx=(8, 0))

    update_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    update_panel.pack(fill="x", pady=(0, 12))
    app.settings_update_tag = RoundedTag(update_panel, text="版本更新", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_update_tag.pack(anchor="w")
    update_row = tk.Frame(update_panel, bg=app.card_color)
    update_row.pack(fill="x", pady=(10, 0))
    app.update_status_label = tk.Label(update_row, textvariable=app.update_status_var, bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10), anchor="w")
    app.update_status_label.pack(side="left", fill="x", expand=True)
    app.check_update_button = ttk.Button(update_row, text="检查更新", command=app._check_for_updates)
    app.check_update_button.pack(side="left", padx=(8, 0))
    app.download_update_button = ttk.Button(update_row, text="下载新版", command=app._open_update_download, state="disabled")
    app.download_update_button.pack(side="left", padx=(8, 0))
    app.release_page_button = ttk.Button(update_row, text="发布页", command=app._open_release_page, state="disabled")
    app.release_page_button.pack(side="left", padx=(8, 0))

    highlight_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    highlight_panel.pack(fill="x", pady=(0, 12))
    app.settings_highlight_tag = RoundedTag(highlight_panel, text="Learning Word Highlight", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_highlight_tag.pack(anchor="w")
    highlight_row = tk.Frame(highlight_panel, bg=app.card_color)
    highlight_row.pack(fill="x", pady=(10, 0))
    app.highlight_toggle_check = tk.Checkbutton(
        highlight_row,
        text="Enable story highlight",
        variable=app.highlight_learning_words_var,
        command=app._toggle_learning_word_highlight,
        bg=app.card_color,
        fg=app.text_secondary,
        activebackground=app.card_color,
        activeforeground=app.text_secondary,
        selectcolor=app.card_color,
        highlightthickness=0,
        bd=0,
    )
    app.highlight_toggle_check.pack(side="left")
    color_row = tk.Frame(highlight_panel, bg=app.card_color)
    color_row.pack(fill="x", pady=(8, 0))
    app.highlight_color_block = tk.Label(color_row, width=3, height=1, relief="flat", bd=0, bg=app.config.learning_highlight_color, highlightthickness=1)
    app.highlight_color_block.pack(side="left")
    app.highlight_color_text = tk.Label(color_row, textvariable=app.learning_highlight_color_var, font=(app.en_font_family, 10), bg=app.card_color, fg=app.text_secondary)
    app.highlight_color_text.pack(side="left", padx=(10, 14))
    app.highlight_color_button = ttk.Button(color_row, text="Change", command=app._choose_learning_highlight_color)
    app.highlight_color_button.pack(side="left")

    tips_gallery_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    tips_gallery_panel.pack(fill="x", pady=(0, 12))
    app.settings_tips_tag = RoundedTag(tips_gallery_panel, text="Tips 图鉴", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_tips_tag.pack(anchor="w")
    tips_gallery_row = tk.Frame(tips_gallery_panel, bg=app.card_color)
    tips_gallery_row.pack(fill="x", pady=(10, 0))
    tips_gallery_hint = tk.Label(
        tips_gallery_row,
        text="查看你已经见过的所有Tips，以及还在等待邂逅的那些小彩蛋。",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 10),
    )
    tips_gallery_hint.pack(side="left")
    tk.Frame(tips_gallery_row, bg=app.card_color).pack(side="left", fill="x", expand=True)
    tips_gallery_button = ttk.Button(tips_gallery_row, text="打开图鉴", command=app._show_tips_gallery)
    tips_gallery_button.pack(side="left", padx=(8, 0))

    app.settings_status_var = tk.StringVar(value="")
    app.settings_status_label = tk.Label(app.settings_content, textvariable=app.settings_status_var, bg=app.bg_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.settings_status_label.pack(anchor="w", pady=(8, 0))

    prompt_panel = tk.Frame(app.settings_content, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    prompt_panel.pack(fill="both", expand=True, pady=(0, 12))
    prompt_header = tk.Frame(prompt_panel, bg=app.card_color)
    prompt_header.pack(fill="x")
    app.settings_prompt_tag = RoundedTag(prompt_header, text="故事提示词", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.settings_prompt_tag.pack(side="left")
    app.update_prompt_button = ttk.Button(prompt_header, text="更新提示词", command=app._update_story_prompt)
    app.update_prompt_button.pack(side="right")
    app.story_prompt_text = tk.Text(prompt_panel, height=8, relief="flat", bd=0, padx=10, pady=8, wrap="word")
    app.story_prompt_text.pack(fill="both", expand=True, pady=(10, 0))
    app.story_prompt_text.insert("1.0", app.config.story_prompt)
    app.story_prompt_save_button = ttk.Button(prompt_panel, text="保存提示词", command=app._save_story_prompt)
    app.story_prompt_save_button.pack(anchor="e", pady=(8, 0))

    def _on_prompt_mousewheel(event):
        if hasattr(event, "delta") and event.delta:
            app.story_prompt_text.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            app.story_prompt_text.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            app.story_prompt_text.yview_scroll(1, "units")
        return "break"

    _bind_settings_mousewheel(app.settings_content)
    app.story_prompt_text.bind("<MouseWheel>", _on_prompt_mousewheel)
    app.story_prompt_text.bind("<Button-4>", _on_prompt_mousewheel)
    app.story_prompt_text.bind("<Button-5>", _on_prompt_mousewheel)
    app.settings_scroll_canvas.yview_moveto(0)

    app.settings_page_tags = [
        app.settings_title,
        app.settings_theme_tag,
        app.settings_font_tag,
        app.settings_api_tag,
        app.settings_account_tag,
        app.settings_update_tag,
        app.settings_highlight_tag,
        app.settings_tips_tag,
        app.settings_prompt_tag,
    ]
    app.settings_page_panels = [
        color_panel,
        font_panel,
        api_panel,
        account_panel,
        update_panel,
        highlight_panel,
        tips_gallery_panel,
        prompt_panel,
    ]

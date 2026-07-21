import tkinter as tk
from tkinter import ttk


def build_study_page(app):
    mix = app.mix_color
    RoundedTag = app.RoundedTag
    app.study_page = tk.Frame(app.root, bg=app.bg_color, padx=34, pady=28)
    header_row = tk.Frame(app.study_page, bg=app.bg_color)
    header_row.pack(fill="x")
    app.study_back_button = ttk.Button(header_row, text="← 返回", command=app._back_to_main)
    app.study_back_button.pack(side="left")
    app.study_title = RoundedTag(header_row, text="学习模块", text_font=(app.cn_font_family, 18, "bold"), bg=app.bg_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.86), outline=app.config.theme_color, radius=16, padx=20, pady=8)
    app.study_title.pack(side="left", padx=(18, 0))

    control_panel = tk.Frame(app.study_page, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    control_panel.pack(fill="x", pady=(16, 12))
    app.study_control_tag = RoundedTag(control_panel, text="背诵设置", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.study_control_tag.pack(anchor="w")
    control_row = tk.Frame(control_panel, bg=app.card_color)
    control_row.pack(fill="x", pady=(10, 0))
    app.study_count_label = tk.Label(control_row, text="抽词数量(5-20)", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.study_count_label.pack(side="left")
    app.study_count_spinbox = tk.Spinbox(control_row, from_=5, to=20, textvariable=app.study_word_count_var, width=6, command=app._save_study_word_count, font=(app.en_font_family, 10))
    app.study_count_spinbox.pack(side="left", padx=(8, 10))
    app.study_difficulty_label = tk.Label(control_row, text="Difficulty", bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.study_difficulty_label.pack(side="left")
    app.study_difficulty_combo = ttk.Combobox(control_row, textvariable=app.study_difficulty_var, values=("easy", "normal", "hard"), state="readonly", width=8)
    app.study_difficulty_combo.pack(side="left", padx=(8, 12))
    app.study_difficulty_combo.bind("<<ComboboxSelected>>", app._on_study_difficulty_change)
    app.study_generate_button = ttk.Button(control_row, text="生成故事", command=app._generate_study_story)
    app.study_generate_button.pack(side="left")
    app.study_submit_button = ttk.Button(control_row, text="提交", command=app._submit_study_answers)
    app.study_submit_button.pack(side="left", padx=(8, 0))
    app.study_history_button = ttk.Button(control_row, text="历史学习记录", command=app._open_study_history)
    app.study_history_button.pack(side="left", padx=(8, 0))
    tk.Frame(control_row, bg=app.card_color).pack(side="left", fill="x", expand=True)
    app.quick_lookup_entry = ttk.Entry(control_row, textvariable=app.quick_lookup_var, width=24)
    app.quick_lookup_entry.pack(side="left", padx=(8, 6))
    app.quick_lookup_entry.bind("<Return>", app._quick_lookup_word)
    app.quick_lookup_button = ttk.Button(control_row, text="Lookup", command=app._quick_lookup_word)
    app.quick_lookup_button.pack(side="left")


    body_panel = tk.Frame(app.study_page, bg=app.bg_color)
    body_panel.pack(fill="both", expand=True)
    body_panel.grid_columnconfigure(0, weight=5)
    body_panel.grid_columnconfigure(1, weight=1)
    body_panel.grid_rowconfigure(0, weight=1)

    def _enforce_body_ratio(_event=None):
        total = max(1, body_panel.winfo_width())
        # Two columns with 8px gap on each side between cards.
        usable = max(1, total - 16)
        right = max(1, usable // 6)
        left = max(1, usable - right)
        body_panel.grid_columnconfigure(0, minsize=left)
        body_panel.grid_columnconfigure(1, minsize=right)

    body_panel.bind("<Configure>", _enforce_body_ratio, add="+")

    story_panel = tk.Frame(body_panel, bg=app.card_color, highlightthickness=0, bd=0, padx=20, pady=16)
    story_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    app.study_story_tag = RoundedTag(story_panel, text="故事(Markdown)与答题", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=16, pady=7)
    app.study_story_tag.pack(anchor="w")
    app.study_status_label = tk.Label(story_panel, textvariable=app.study_status_var, bg=app.card_color, fg=app.text_secondary, font=(app.cn_font_family, 10))
    app.study_status_label.pack(anchor="w", pady=(8, 8))

    app.story_text_container = tk.Frame(story_panel, bg=app.card_color)
    app.story_text_container.pack(fill="both", expand=True)
    app.study_story_text = tk.Text(app.story_text_container, relief="flat", bd=0, padx=10, pady=8, wrap="word", width=1)
    app.study_story_text.pack(fill="both", expand=True)

    def _on_story_mousewheel(event):
        if hasattr(event, "delta") and event.delta:
            app.study_story_text.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            app.study_story_text.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            app.study_story_text.yview_scroll(1, "units")
        return "break"

    app.study_story_text.bind("<MouseWheel>", _on_story_mousewheel)
    app.study_story_text.bind("<Button-4>", _on_story_mousewheel)
    app.study_story_text.bind("<Button-5>", _on_story_mousewheel)
    app.study_story_text.bind("<ButtonRelease-1>", app._lookup_selected_story_text, add="+")

    answer_card = tk.Frame(body_panel, bg=app.card_color, highlightthickness=0, bd=0, padx=12, pady=16)
    answer_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    app.quick_lookup_output_tag = RoundedTag(answer_card, text="\u67e5\u8be2\u7ed3\u679c", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=12, pady=7)
    app.quick_lookup_output_tag.pack(anchor="w")
    app.quick_lookup_output_text = tk.Text(
        answer_card,
        height=6,
        width=1,
        wrap="word",
        relief="flat",
        bd=0,
        padx=10,
        pady=8,
        bg=mix(app.config.theme_color, "#ffffff", 0.93),
        fg=app.text_color,
        font=(app.cn_font_family, 10),
    )
    app.quick_lookup_output_text.pack(fill="x", expand=False, pady=(8, 10))
    app.quick_lookup_output_text.configure(state="disabled")

    def _on_quick_output_mousewheel(event):
        if hasattr(event, "delta") and event.delta:
            app.quick_lookup_output_text.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            app.quick_lookup_output_text.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            app.quick_lookup_output_text.yview_scroll(1, "units")
        return "break"

    app.quick_lookup_output_text.bind("<MouseWheel>", _on_quick_output_mousewheel)
    app.quick_lookup_output_text.bind("<Button-4>", _on_quick_output_mousewheel)
    app.quick_lookup_output_text.bind("<Button-5>", _on_quick_output_mousewheel)
    app._sync_quick_lookup_output()

    app.study_answer_tag = RoundedTag(answer_card, text="中文答案", text_font=(app.cn_font_family, 12, "bold"), bg=app.card_color, fg=app.config.theme_color, fill=mix(app.config.theme_color, "#ffffff", 0.88), outline=app.config.theme_color, radius=14, padx=12, pady=7)
    app.study_answer_tag.pack(anchor="w")

    app.answer_scroll_container = tk.Frame(answer_card, bg=app.card_color)
    app.answer_scroll_container.pack(fill="both", expand=True, pady=(10, 0))
    app.answer_canvas = tk.Canvas(app.answer_scroll_container, bg=app.card_color, highlightthickness=0, bd=0)
    app.answer_canvas.pack(fill="both", expand=True)
    app.answer_panel = tk.Frame(app.answer_canvas, bg=app.card_color)
    app.answer_canvas_window = app.answer_canvas.create_window((0, 0), window=app.answer_panel, anchor="nw")

    def _on_answer_panel_configure(_event=None):
        app.answer_canvas.configure(scrollregion=app.answer_canvas.bbox("all"))

    def _on_answer_canvas_configure(event):
        app.answer_canvas.itemconfigure(app.answer_canvas_window, width=event.width)

    def _on_answer_mousewheel(event):
        if hasattr(event, "delta") and event.delta:
            app.answer_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            app.answer_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            app.answer_canvas.yview_scroll(1, "units")
        return "break"

    app._on_answer_mousewheel = _on_answer_mousewheel
    app.answer_panel.bind("<Configure>", _on_answer_panel_configure)
    app.answer_canvas.bind("<Configure>", _on_answer_canvas_configure)
    app.answer_canvas.bind("<MouseWheel>", _on_answer_mousewheel)
    app.answer_canvas.bind("<Button-4>", _on_answer_mousewheel)
    app.answer_canvas.bind("<Button-5>", _on_answer_mousewheel)

    app.study_page_tags = [app.study_title, app.study_control_tag, app.study_story_tag, app.quick_lookup_output_tag, app.study_answer_tag]
    app.study_page_panels = [control_panel, story_panel, answer_card]

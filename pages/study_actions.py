import json
import os
import re
import threading
from datetime import datetime
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from tkinter import ttk

from services.llm_service import LLMService


def _base_dir():
    import sys as _sys
    if getattr(_sys, "frozen", False):
        return os.path.dirname(_sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_study_story(app):
    app._load_env_settings()
    app._refresh_env_labels()
    if not app.api_key:
        app.study_status_var.set("请在 .env 中配置 API_KEY")
        return
    app.current_story_plain = ""
    app.current_story_md_path = ""
    app._save_study_word_count()
    app._save_study_difficulty()
    words = app.dictionary_service.get_learning_words(app.config.study_word_count)
    blocked_words = {"linger", "hyacinth"}
    words = [w for w in words if (w or "").strip().lower() not in blocked_words]
    if not words:
        app.study_status_var.set("“正在背”词库为空，请先添加单词")
        return
    word_lines = []
    app.current_quiz_words = []
    app.current_quiz_word_set = set()
    for idx, word in enumerate(words, 1):
        data = app.dictionary_service.get_word_data(word)
        translation = (data or {}).get("translation") or ""
        translation = translation.strip() if isinstance(translation, str) else ""
        app.current_quiz_words.append({"index": idx, "word": word, "translation": translation})
        app.current_quiz_word_set.add((word or "").strip().lower())
        word_lines.append(f"{idx}. {word} - {translation}")
    prompt_template = app._get_story_prompt_for_generation()
    difficulty_prompt = app._build_story_difficulty_prompt()
    prompt = (
        prompt_template.strip()
        + "\n\n"
        + difficulty_prompt
        + "\n\nWord List:\n"
        + "\n".join(word_lines)
    )
    app.study_status_var.set("正在请求 LLM 生成故事...")
    app._set_study_controls_enabled(False)
    app._show_study_loading("铃兰在编织故事")
    app.story_request_seq += 1
    request_id = app.story_request_seq
    app.active_story_request_id = request_id
    app.root.after(15000, lambda: app._check_story_timeout(request_id))
    worker = threading.Thread(target=app._generate_story_worker, args=(prompt, request_id), daemon=True)
    worker.start()


def generate_story_worker(app, prompt, request_id):
    try:
        story = app._call_llm(prompt)
        app.root.after(0, lambda rid=request_id, s=story: app._on_story_generated(rid, s))
    except Exception as e:
        error_message = str(e)
        app.root.after(0, lambda rid=request_id, msg=error_message: app._on_story_failed(rid, msg))


def check_story_timeout(app, request_id):
    if app.active_story_request_id != request_id:
        return
    app.active_story_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    app.study_status_var.set("生成超时，请检查网络/API后重试")


def call_llm(app, prompt):
    service = LLMService(app.base_url, app.api_key)
    return service.call_chat(prompt)


def configure_story_markdown_tags(app):
    if not hasattr(app, "study_story_text"):
        return
    base_font = tkfont.Font(font=app.study_story_text.cget("font"))
    bold_font = tkfont.Font(font=app.study_story_text.cget("font"))
    bold_font.configure(weight="bold")
    app.story_text_fonts["base"] = base_font
    app.story_text_fonts["bold"] = bold_font
    app.study_story_text.tag_configure("md_bold", font=bold_font)
    highlight_color = getattr(app.config, "learning_highlight_color", "#fff4b8")
    app.study_story_text.tag_configure("md_learning_word", background=highlight_color)
    app.study_story_text.tag_raise("md_bold")


def highlight_learning_words_in_story(app):
    if not hasattr(app, "study_story_text"):
        return
    app.study_story_text.tag_remove("md_learning_word", "1.0", tk.END)
    if not getattr(app.config, "highlight_learning_words", True):
        return
    learning_words = app.dictionary_service.list_words("learning")
    learning_set = {
        (word or "").strip().lower()
        for word in learning_words
        if isinstance(word, str) and (word or "").strip()
    }
    if not learning_set:
        return
    content = app.study_story_text.get("1.0", "end-1c")
    if not content:
        return
    for match in re.finditer(r"[A-Za-z][A-Za-z'-]*", content):
        token = (match.group(0) or "").strip("-'").lower()
        if not token or token not in learning_set:
            continue
        start = f"1.0+{match.start()}c"
        end = f"1.0+{match.end()}c"
        app.study_story_text.tag_add("md_learning_word", start, end)
    app.study_story_text.tag_raise("md_bold")


def save_story_markdown(app, markdown_text):
    output_dir = os.path.join(_base_dir(), "study_stories")
    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.now().strftime("story_%Y%m%d_%H%M%S.md")
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    return output_path


def build_history_markdown(app, story_text, rows, correct_count, total_count, moved_words):
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story_body = (story_text or "").strip()
    if not story_body:
        story_body = app.study_story_text.get("1.0", tk.END).strip()
    lines = [
        "# 历史学习记录",
        "",
        f"- 提交时间：{submitted_at}",
        f"- 总题数：{total_count}",
        f"- 正确数：{correct_count}",
    ]
    if moved_words:
        lines.append("- 本次移入背诵完成：" + "、".join(moved_words))
    lines.extend([
        "",
        "## 故事",
        "",
        story_body or "（无故事内容）",
        "",
        "## 作答记录",
        "",
    ])
    for row in rows:
        user_answer = (row.get("user_answer") or "").strip() or "（空）"
        reference = (row.get("reference") or "").replace("\n", " / ").strip() or "（无）"
        verdict = "可取" if row.get("is_correct") else "不可取"
        reason = (row.get("reason") or "").replace("\n", " / ").strip() or "（无）"
        streak = row.get("streak")
        moved = row.get("moved")
        lines.extend([
            f"### {row.get('index')}. {row.get('word')}",
            f"- 用户回答：{user_answer}",
            f"- 参考释义：{reference}",
            f"- 判定：{verdict}",
            f"- 评语：{reason}",
            f"- 连对次数：{streak}",
            f"- 状态：{'已移入背诵完成' if moved else '仍在正在背'}",
            "",
        ])
    return "\n".join(lines).strip() + "\n"


def list_study_history_files(app):
    history_dir = os.path.join(_base_dir(), "study_stories")
    if not os.path.exists(history_dir):
        return []
    file_names = [name for name in os.listdir(history_dir) if name.lower().endswith(".md")]
    file_names.sort(reverse=True)
    return [os.path.join(history_dir, name) for name in file_names]


def load_history_file_text(app, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def open_study_history(app):
    history_files = app._list_study_history_files()
    if not history_files:
        messagebox.showinfo("历史学习记录", "暂无历史学习记录")
        return
    if app.study_history_window and app.study_history_window.winfo_exists():
        app.study_history_window.lift()
        app.study_history_window.focus_force()
        return
    win = tk.Toplevel(app.root)
    app.study_history_window = win
    win.title("历史学习记录")
    win.geometry("980x700")
    win.minsize(860, 580)
    win.configure(bg=app.bg_color)

    container = tk.Frame(win, bg=app.bg_color, padx=12, pady=12)
    container.pack(fill="both", expand=True)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=3)
    container.grid_rowconfigure(1, weight=1)

    title = app.RoundedTag(
        container,
        text="历史学习记录",
        text_font=(app.cn_font_family, 14, "bold"),
        bg=app.bg_color,
        fg=app.config.theme_color,
        fill=app.mix_color(app.config.theme_color, "#ffffff", 0.88),
        outline=app.config.theme_color,
        radius=14,
        padx=18,
        pady=8,
    )
    title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    list_panel = tk.Frame(container, bg=app.card_color, padx=10, pady=10)
    list_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    view_panel = tk.Frame(container, bg=app.card_color, padx=10, pady=10)
    view_panel.grid(row=1, column=1, sticky="nsew")

    tk.Label(
        list_panel,
        text="记录文件",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 11, "bold"),
    ).pack(anchor="w")
    file_listbox = tk.Listbox(
        list_panel,
        relief="flat",
        bd=0,
        font=(app.en_font_family, 10),
    )
    file_listbox.pack(fill="both", expand=True, pady=(8, 0))
    for path in history_files:
        file_listbox.insert(tk.END, os.path.basename(path))

    tk.Label(
        view_panel,
        text="记录详情",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 11, "bold"),
    ).pack(anchor="w")
    text_container = tk.Frame(view_panel, bg=app.card_color)
    text_container.pack(fill="both", expand=True, pady=(8, 0))
    record_text = tk.Text(
        text_container,
        wrap="word",
        relief="flat",
        bd=0,
        padx=10,
        pady=8,
        font=(app.en_font_family, 10),
        bg=app.card_color,
        fg=app.text_color,
        insertbackground=app.text_color,
    )
    scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=record_text.yview)
    record_text.configure(yscrollcommand=scrollbar.set)
    record_text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def show_record(index):
        if index < 0 or index >= len(history_files):
            return
        target = history_files[index]
        try:
            content = app._load_history_file_text(target)
        except Exception as e:
            content = f"读取失败：{e}"
        record_text.configure(state="normal")
        record_text.delete("1.0", tk.END)
        record_text.insert("1.0", content)
        record_text.configure(state="disabled")

    def on_select(_event=None):
        selected = file_listbox.curselection()
        if not selected:
            return
        show_record(selected[0])

    file_listbox.bind("<<ListboxSelect>>", on_select)
    file_listbox.selection_set(0)
    show_record(0)


def render_story_markdown(app, markdown_text):
    text = (markdown_text or "").strip()
    app.study_story_text.configure(state="normal")
    app.study_story_text.delete("1.0", tk.END)
    app._configure_story_markdown_tags()
    cursor = 0
    for match in re.finditer(r"\*\*(.+?)\*\*", text, flags=re.DOTALL):
        start, end = match.span()
        if start > cursor:
            app.study_story_text.insert(tk.END, text[cursor:start])
        bold_text = (match.group(1) or "").strip()
        app.study_story_text.insert(tk.END, bold_text, ("md_bold",))
        cursor = end
    if cursor < len(text):
        app.study_story_text.insert(tk.END, text[cursor:])
    app._highlight_learning_words_in_story()
    app.study_story_text.configure(state="disabled")


def on_story_generated(app, request_id, story):
    if app.active_story_request_id != request_id:
        return
    app.active_story_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    app.current_story_plain = (story or "").strip()
    app.current_story_md_path = ""
    app._render_story_markdown(app.current_story_plain)
    app.current_quiz_words = app._extract_story_order(story, app.current_quiz_words)
    app._build_answer_inputs()
    app.study_status_var.set("故事已生成，请填写答案并提交；提交后将写入历史学习记录")


def on_story_failed(app, request_id, message):
    if app.active_story_request_id != request_id:
        return
    app.active_story_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    app.current_story_plain = ""
    app.current_story_md_path = ""
    app.study_status_var.set(f"生成失败：{message}")


def build_answer_inputs(app):
    for widget in app.answer_panel.winfo_children():
        widget.destroy()
    app.answer_entries = []
    app.answer_result_labels = []
    app.answer_blocks = []
    for item in app.current_quiz_words:
        block = tk.Frame(app.answer_panel, bg=app.card_color)
        block.pack(fill="x", pady=(0, 8), anchor="n")
        row = tk.Frame(block, bg=app.card_color)
        row.pack(fill="x")
        number_label = tk.Label(
            row,
            text=f"{item['index']}.",
            bg=app.card_color,
            fg=app.text_color,
            width=4,
            anchor="w",
            font=(app.en_font_family, 10),
        )
        number_label.pack(side="left")
        answer_var = tk.StringVar(value="")
        entry = ttk.Entry(row, textvariable=answer_var)
        entry.pack(side="left", fill="x", expand=True, padx=(4, 6))
        result_label = tk.Label(
            block,
            text="",
            bg=app.card_color,
            fg=app.text_color,
            anchor="w",
            justify="left",
            wraplength=170,
            font=(app.cn_font_family, 10),
        )
        result_label.pack(fill="x", padx=(30, 2), pady=(4, 0))
        if hasattr(app, "_on_answer_mousewheel"):
            for widget in (block, row, number_label, entry, result_label):
                widget.bind("<MouseWheel>", app._on_answer_mousewheel, add="+")
                widget.bind("<Button-4>", app._on_answer_mousewheel, add="+")
                widget.bind("<Button-5>", app._on_answer_mousewheel, add="+")
        app.answer_entries.append((item, answer_var, entry))
        app.answer_result_labels.append(result_label)
        app.answer_blocks.append(block)
    for idx, (_, _, entry) in enumerate(app.answer_entries):
        entry.bind("<Return>", lambda event, i=idx: app._focus_answer_index(i + 1))
        entry.bind("<Down>", lambda event, i=idx: app._focus_answer_index(i + 1))
        entry.bind("<Up>", lambda event, i=idx: app._focus_answer_index(i - 1))
    if app.answer_entries:
        app.answer_entries[0][2].focus_set()
    if hasattr(app, "answer_canvas"):
        app.answer_canvas.update_idletasks()
        app.answer_canvas.configure(scrollregion=app.answer_canvas.bbox("all"))
        app.answer_canvas.yview_moveto(0)


def focus_answer_index(app, index):
    if not app.answer_entries:
        return "break"
    total = len(app.answer_entries)
    index = max(0, min(total - 1, index))
    app.answer_entries[index][2].focus_set()
    return "break"


def feedback_gap(app, message):
    text = (message or "").strip()
    if not text:
        return 8
    logical_lines = text.count("\n") + 1
    approx_wrapped_lines = max(1, (len(text) // 18) + 1)
    visual_lines = max(logical_lines, approx_wrapped_lines)
    return min(28, 8 + (visual_lines - 1) * 4)


def set_answer_feedback(app, index, message, color):
    if index < 0 or index >= len(app.answer_result_labels):
        return
    feedback_text = (message or "").strip()
    app.answer_result_labels[index].configure(fg=color, text=feedback_text)
    if index < len(app.answer_blocks):
        app.answer_blocks[index].pack_configure(pady=(0, app._feedback_gap(feedback_text)))


def extract_story_order(app, story, default_items):
    items_by_word = {item["word"].lower(): item for item in default_items}
    matches = re.finditer(r"\*\*([^*]+)\*\*\s*\((\d+)\)", story or "")
    ordered = []
    used_numbers = set()
    for match in matches:
        word = (match.group(1) or "").strip().lower()
        number = int(match.group(2))
        if number in used_numbers:
            continue
        item = items_by_word.get(word)
        if not item:
            continue
        copied = dict(item)
        copied["index"] = number
        ordered.append(copied)
        used_numbers.add(number)
    if not ordered:
        return default_items
    ordered.sort(key=lambda x: x["index"])
    return ordered


def quick_lookup_word(app, _event=None):
    keyword = app.quick_lookup_var.get().strip()
    if not keyword:
        app._set_quick_lookup_result("请输入英文单词")
        return
    if keyword.lower() in app.current_quiz_word_set:
        app._set_quick_lookup_result("这一题要靠自己想哦！")
        return
    result = app.dictionary_service.search_word(keyword)
    if not result:
        app._set_quick_lookup_result("未找到")
        return
    translation = (result.get("translation") or "").strip()
    if not translation:
        app._set_quick_lookup_result("暂无中文释义")
        return
    concise = translation.split("\n")[0].split("；")[0].split(";")[0].strip()
    app._set_quick_lookup_result(concise or "暂无中文释义")




def lookup_selected_story_text(app, _event=None):
    if not hasattr(app, "study_story_text"):
        return
    try:
        selected = app.study_story_text.selection_get()
    except tk.TclError:
        return
    keyword = app._normalize_lookup_text(selected)
    if not keyword:
        return
    try:
        message = app._lookup_meaning_brief(keyword)
    except Exception as e:
        message = f"selection lookup failed: {e}"
    app._set_quick_lookup_result(message)

def extract_json_block(app, text):
    content = (text or "").strip()
    if content.startswith("{") and content.endswith("}"):
        return content
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start : end + 1]
    return ""


def judge_answers_with_llm(app, story, items):
    prompt = (
        "你是中文释义评审器。请根据英文故事语境与参考释义判断用户答案是否可取。"
        "请只输出JSON对象，格式：{\"results\":[{\"index\":1,\"acceptable\":true,\"reason\":\"简短中文\"}]}"
        "reason不要超过16个汉字。\n"
        f"故事：\n{story}\n"
        f"评审列表：\n{json.dumps(items, ensure_ascii=False)}"
    )
    response = app._call_llm(prompt)
    json_block = app._extract_json_block(response)
    if not json_block:
        raise RuntimeError("评审结果解析失败")
    data = json.loads(json_block)
    results = data.get("results")
    if not isinstance(results, list):
        raise RuntimeError("评审结果格式错误")
    mapped = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        idx = row.get("index")
        if isinstance(idx, int):
            mapped[idx] = row
    return mapped


def submit_review_worker(app, story, items, request_id):
    try:
        review_map = app._judge_answers_with_llm(story, items)
        app.root.after(0, lambda rid=request_id, rm=review_map, rows=items, s=story: app._on_submit_review_success(rid, rm, rows, s))
    except Exception as e:
        message = str(e)
        app.root.after(0, lambda rid=request_id, msg=message: app._on_submit_review_failed(rid, msg))


def check_review_timeout(app, request_id):
    if app.active_review_request_id != request_id:
        return
    app.active_review_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    app.study_status_var.set("评审超时，请检查网络/API后重试")


def on_submit_review_success(app, request_id, review_map, submitted_items, story_text):
    if app.active_review_request_id != request_id:
        return
    app.active_review_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    moved_words = []
    correct_count = 0
    history_rows = []
    for idx, submitted in enumerate(submitted_items):
        word = submitted.get("word", "")
        standard = (submitted.get("reference") or "").strip()
        review = review_map.get(submitted.get("index"), {})
        is_correct = bool(review.get("acceptable"))
        reason = (review.get("reason") or "").strip()
        user_answer = (submitted.get("user_answer") or "").strip()
        streak, moved = app.dictionary_service.update_streak_and_maybe_finish(word, is_correct)
        if is_correct:
            correct_count += 1
            message = f"可取（连对{streak}次）"
            if reason:
                message += f"\n{reason}"
            app._set_answer_feedback(idx, message, "#1e8f4d")
        else:
            message = f"不可取\n参考：{standard}"
            if reason:
                message += f"\n{reason}"
            app._set_answer_feedback(idx, message, "#c94343")
        if moved:
            moved_words.append(word)
        history_rows.append(
            {
                "index": submitted.get("index"),
                "word": word,
                "reference": standard,
                "user_answer": user_answer,
                "is_correct": is_correct,
                "reason": reason,
                "streak": streak,
                "moved": moved,
            }
        )
    app._refresh_personal_lists()
    history_save_error = ""
    try:
        history_markdown = app._build_history_markdown(
            story_text,
            history_rows,
            correct_count,
            len(submitted_items),
            moved_words,
        )
        app.current_story_md_path = app._save_story_markdown(history_markdown)
    except Exception as e:
        app.current_story_md_path = ""
        history_save_error = str(e)
    if moved_words:
        status_message = "本次完成移入背诵完成：" + "、".join(moved_words)
    else:
        status_message = f"提交完成：{correct_count}/{len(submitted_items)} 正确"
    if app.current_story_md_path:
        status_message += f" | 已记录：{os.path.basename(app.current_story_md_path)}"
    elif history_save_error:
        status_message += f" | 记录保存失败：{history_save_error}"
    app.study_status_var.set(status_message)


def on_submit_review_failed(app, request_id, message):
    if app.active_review_request_id != request_id:
        return
    app.active_review_request_id = 0
    app._hide_study_loading()
    app._set_study_controls_enabled(True)
    app.study_status_var.set(f"评审失败：{message}")


def submit_study_answers(app):
    if not app.answer_entries:
        app.study_status_var.set("请先生成故事")
        return
    app._load_env_settings()
    if not app.api_key:
        app.study_status_var.set("请在设置中配置 API_KEY")
        return
    story = (app.current_story_plain or "").strip()
    if not story:
        story = app.study_story_text.get("1.0", tk.END).strip()
    submitted_items = []
    for item, answer_var, _ in app.answer_entries:
        submitted_items.append(
            {
                "index": item.get("index"),
                "word": item.get("word"),
                "reference": item.get("translation", ""),
                "user_answer": answer_var.get().strip(),
            }
        )
    app.study_status_var.set("正在进行LLM评审...")
    app._set_study_controls_enabled(False)
    app._show_study_loading("铃兰在批改答案")
    app.review_request_seq += 1
    request_id = app.review_request_seq
    app.active_review_request_id = request_id
    app.root.after(20000, lambda: app._check_review_timeout(request_id))
    worker = threading.Thread(
        target=app._submit_review_worker,
        args=(story, submitted_items, request_id),
        daemon=True,
    )
    worker.start()

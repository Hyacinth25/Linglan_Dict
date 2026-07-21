import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox


def add_single_word(app, _event=None):
    keyword = app.add_word_var.get().strip()
    ok, message = app.dictionary_service.add_word_to_learning(keyword)
    app.add_status_var.set(message)
    if ok:
        app.add_word_var.set("")
        app._refresh_personal_lists()


def select_import_file(app):
    path = filedialog.askopenfilename(
        title="选择txt文件",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
    )
    if path:
        app.import_file_var.set(path)


def import_words(app):
    path = app.import_file_var.get().strip()
    result = app.dictionary_service.import_words_from_txt(path)
    total = result.get("total", 0)
    added = result.get("added", 0)
    missing = result.get("missing", 0)
    learned = result.get("learned", 0)
    existing = result.get("existing", 0)
    message = f"导入完成：总数{total}，新增{added}，词库不存在{missing}"
    if learned:
        message += f"，已背诵不可重复添加{learned}"
    if existing:
        message += f"，正在背已存在{existing}"
    app.add_status_var.set(message)
    app._refresh_personal_lists()


def export_learning_words(app):
    words = app.dictionary_service.list_words("learning")
    if not words:
        app.add_status_var.set("“正在背”词库为空，无可导出单词")
        return
    path = filedialog.asksaveasfilename(
        title="导出正在背单词表",
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        initialfile="正在背单词表.txt",
    )
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(words))
    app.add_status_var.set(f"导出完成：{len(words)} 个单词")


def refresh_personal_lists(app):
    if not hasattr(app, "learning_listbox"):
        return
    learning_words = app.dictionary_service.list_words("learning")
    finished_words = app.dictionary_service.list_words("finished")
    app.learning_tag.set_text(f"正在背（{len(learning_words)}）")
    app.finished_tag.set_text(f"背诵完成（{len(finished_words)}）")
    app.learning_listbox.delete(0, tk.END)
    app.finished_listbox.delete(0, tk.END)
    for word in learning_words:
        app.learning_listbox.insert(tk.END, word)
    for word in finished_words:
        app.finished_listbox.insert(tk.END, word)


def open_word_menu(app, event, list_name):
    listbox = app.learning_listbox if list_name == "learning" else app.finished_listbox
    if listbox.size() == 0:
        return
    index = listbox.nearest(event.y)
    if index < 0:
        return
    listbox.selection_clear(0, tk.END)
    listbox.selection_set(index)
    app.word_menu_target = listbox.get(index)
    app.word_menu_list_name = list_name
    try:
        app.word_menu.tk_popup(event.x_root, event.y_root)
    finally:
        app.word_menu.grab_release()


def query_menu_word(app):
    if not app.word_menu_target:
        return
    app._show_word_query(app.word_menu_target)


def remove_menu_word(app):
    if not app.word_menu_target or not app.word_menu_list_name:
        return
    removed = app.dictionary_service.remove_word_from_list(app.word_menu_target, app.word_menu_list_name)
    if removed:
        app.add_status_var.set(f"已移出：{app.word_menu_target}")
    else:
        app.add_status_var.set(f"未移出：{app.word_menu_target}")
    app._refresh_personal_lists()


def query_selected_word(app, list_name):
    listbox = app.learning_listbox if list_name == "learning" else app.finished_listbox
    selection = listbox.curselection()
    if not selection:
        return
    app._show_word_query(listbox.get(selection[0]))


def show_word_query(app, word):
    result = app.dictionary_service.search_word(word)
    if not result:
        messagebox.showinfo("查询", f"未找到：{word}")
        return
    phonetic = result.get("phonetic") or ""
    pos = result.get("pos") or ""
    definition = result.get("definition") or ""
    translation = result.get("translation") or ""
    lines = [f"单词：{result.get('word') or word}"]
    if phonetic:
        lines.append(f"音标：{phonetic}")
    if pos:
        lines.append(f"词性：{pos}")
    if definition:
        lines.append("")
        lines.append("英文释义：")
        lines.append(definition)
    if translation:
        lines.append("")
        lines.append("中文释义：")
        lines.append(translation)
    messagebox.showinfo("查询结果", "\n".join(lines))

import time
import tkinter as tk
from tkinter import filedialog, messagebox

from services.competition_service import CompetitionService


def get_random_tip(app):
    # Check for special trigger tips first
    if hasattr(app, "tips_service"):
        review_words = app.competition_service.get_today_review_count() * 30
        context = {"review_words": review_words}
        special = app.tips_service.get_special_tip(context)
        if special:
            return special
    # Fall back to regular tips
    if hasattr(app, "tips_service"):
        return app.tips_service.get_random_tip()
    return "灵儿正在努力连接魔法世界，等我一下下哦... (〃'▽'〃)"


def show_random_tip(app):
    tip = get_random_tip(app)
    app.competition_status_var.set(tip)


def format_elapsed(seconds):
    return CompetitionService.format_elapsed(seconds)


def format_rank(rank):
    return CompetitionService.format_rank(rank)


def clamp_start_group(count, start):
    try:
        count_int = int(count)
    except Exception:
        count_int = 1
    if count_int < 1:
        count_int = 1
    try:
        start_int = int(start)
    except Exception:
        start_int = 1
    max_start = max(1, 100 - count_int + 1)
    if start_int < 1:
        start_int = 1
    if start_int > max_start:
        start_int = max_start
    # Snap to valid step: start must be 1, 1+n, 1+2n, ...
    if count_int > 1 and start_int > 1:
        offset = start_int - 1
        step = count_int
        snapped_offset = ((offset + step // 2) // step) * step
        start_int = 1 + snapped_offset
        if start_int > max_start:
            start_int = max_start
            # re-snap from max_start downward
            offset = max_start - 1
            snapped_offset = (offset // step) * step
            start_int = 1 + snapped_offset
        if start_int < 1:
            start_int = 1
    return count_int, start_int


def update_range_label(app):
    count = app.competition_group_count_int
    start = app.competition_start_group_int
    end = start + count - 1
    app.competition_range_var.set(f"→ List {start}-{end}")


def on_count_change(app, _event=None):
    raw = (app.competition_group_count_var.get() or "").strip()
    try:
        count = int(raw)
    except Exception:
        count = app.competition_group_count_int
    if count not in (1, 5, 10, 25, 50):
        count = app.competition_group_count_int if app.competition_group_count_int in (1, 5, 10, 25, 50) else 1
    app.competition_group_count_var.set(str(count))
    count, start = clamp_start_group(count, app.competition_start_group_var.get())
    app.competition_group_count_int = count
    app.competition_start_group_int = start
    app.competition_start_group_var.set(str(start))
    update_range_label(app)
    refresh_history(app)


def on_start_change(app, _event=None):
    raw = (app.competition_start_group_var.get() or "").strip()
    try:
        start = int(raw)
    except Exception:
        start = app.competition_start_group_int
    count, start = clamp_start_group(app.competition_group_count_var.get(), start)
    app.competition_group_count_int = count
    app.competition_start_group_int = start
    app.competition_start_group_var.set(str(start))
    app.competition_group_count_var.set(str(count))
    update_range_label(app)
    refresh_history(app)


def clear_result_labels(app):
    for label in app.competition_result_labels.values():
        label.configure(text="-")


def compute_today_total(app):
    total = app.competition_service.get_today_total_seconds()
    app.competition_today_total_var.set(f"Total：{format_elapsed(total)}")
    review = app.competition_service.get_today_review_count()
    app.competition_review_var.set(f"Review: {review * 30} 词")
    return total


def on_filter_toggle(app):
    refresh_history(app)


def on_key_toggle(app, key):
    """Toggle checkboxes via keyboard keys 1-4."""
    if not hasattr(app, "competition_page") or not app.competition_page.winfo_ismapped():
        return
    var_map = {
        "1": "competition_group_count_filter_var",
        "2": "competition_today_only_var",
        "3": "competition_highlight_same_group_var",
        "4": "competition_filter_var",
    }
    attr = var_map.get(key)
    if attr and hasattr(app, attr):
        var = getattr(app, attr)
        var.set(not var.get())
        on_filter_toggle(app)


def populate_result_labels(app, record):
    start = record.get("start_group")
    end = record.get("end_group")
    gc = record.get("group_count", 1)
    elapsed = record.get("elapsed_seconds", 0.0)
    record_id = record.get("id", "")

    app.competition_result_labels["list_range"].configure(text=f"List {start}-{end}")

    prev_best = app.competition_service.get_previous_best(gc, start, record_id)
    if prev_best is not None:
        prev_elapsed = prev_best.get("elapsed_seconds", 0.0)
        diff = elapsed - prev_elapsed
        sign = "+" if diff >= 0 else ""
        app.competition_result_labels["elapsed"].configure(
            text=f"{format_elapsed(prev_elapsed)} -> {format_elapsed(elapsed)} | {sign}{diff:.1f}s"
        )
    else:
        app.competition_result_labels["elapsed"].configure(text=f"- -> {format_elapsed(elapsed)} | 新纪录")

    group_rank = record.get("rank", 0)
    group_total = 0
    all_records = app.competition_service._load()
    for r in all_records:
        if r.get("group_count") == gc and r.get("start_group") == start:
            group_total += 1
    group_pct = (1 - (group_rank - 1) / max(group_total, 1)) * 100
    app.competition_result_labels["rank"].configure(
        text=f"{format_rank(group_rank)}/{group_total} | {group_pct:.1f}%"
    )

    total_rank, total_count = app.competition_service.get_total_rank_and_count(record_id, gc)
    total_pct = (1 - (total_rank - 1) / max(total_count, 1)) * 100
    app.competition_result_labels["total_rank"].configure(
        text=f"{format_rank(total_rank)}/{total_count} | {total_pct:.1f}%"
    )

    app.competition_result_labels["date"].configure(text=record.get("created_at", ""))
    grade = app.competition_service.get_grade(
        record.get("elapsed_seconds", 0.0), record.get("group_count", 1)
    )
    app.competition_result_labels["grade"].configure(text=grade)
    app.competition_result_labels["remark"].configure(text=record.get("remark", "") or "-")


def refresh_history(app):
    tree = getattr(app, "competition_history_tree", None)
    if tree is None:
        return
    existing_selection = tree.selection()
    for item in tree.get_children():
        tree.delete(item)

    records = app.competition_service.list_records()

    filter_on = getattr(app, "competition_filter_var", None)
    if filter_on is not None and filter_on.get():
        gc = app.competition_group_count_int
        sg = app.competition_start_group_int
        records = [r for r in records if r.get("group_count") == gc and r.get("start_group") == sg]

    gc_filter_on = getattr(app, "competition_group_count_filter_var", None)
    if gc_filter_on is not None and gc_filter_on.get():
        gc = app.competition_group_count_int
        records = [r for r in records if r.get("group_count") == gc]

    today_only_on = getattr(app, "competition_today_only_var", None)
    if today_only_on is not None and today_only_on.get():
        today_str = CompetitionService._today_str()
        records = [r for r in records if r.get("created_at") == today_str]

    app.competition_history_records = records

    gc = app.competition_group_count_int
    sg = app.competition_start_group_int
    latest_id = ""
    latest_ts = -1
    for r in records:
        if r.get("group_count") == gc and r.get("start_group") == sg:
            ts = r.get("created_ts", 0)
            if ts > latest_ts:
                latest_ts = ts
                latest_id = r.get("id")

    tag_current = "current_group"
    tag_latest = "latest_record"
    tag_iridium = "grade_iridium"
    tag_gold = "grade_gold"
    tag_silver = "grade_silver"
    tag_copper = "grade_copper"
    tree.tag_configure(tag_current, background="#FFECF2")
    tree.tag_configure(tag_latest, foreground="#342635")
    tree.tag_configure(tag_iridium, background="#F0E8FF")
    tree.tag_configure(tag_gold, background="#FFF8E0")
    tree.tag_configure(tag_silver, background="#E5E5E5")
    tree.tag_configure(tag_copper, background="#FFF0E0")

    all_records = app.competition_service._load()
    total_ranks = app.competition_service.compute_total_ranks_map(all_records)

    filter_active = filter_on is not None and filter_on.get()
    highlight_on = getattr(app, "competition_highlight_same_group_var", None)
    highlight_active = highlight_on is not None and highlight_on.get()

    for record in records:
        grade = app.competition_service.get_grade(
            record.get("elapsed_seconds", 0.0), record.get("group_count", 1)
        )
        tags = []
        # grade background (lower priority)
        if grade == "Iridium":
            tags.append(tag_iridium)
        elif grade == "Gold":
            tags.append(tag_gold)
        elif grade == "Silver":
            tags.append(tag_silver)
        elif grade == "Copper":
            tags.append(tag_copper)
        # current group highlight (higher priority, overrides grade)
        if record.get("group_count") == gc and record.get("start_group") == sg:
            if not filter_active and highlight_active:
                tags.append(tag_current)
        if record.get("id") == latest_id:
            tags.append(tag_latest)
        rid = record.get("id")
        tr_entry = total_ranks.get(rid, (0, 0))
        total_rank_str = f"{tr_entry[0]}"
        tree.insert(
            "",
            "end",
            iid=rid,
            values=(
                f"List {record.get('start_group')}-{record.get('end_group')}",
                format_elapsed(record.get("elapsed_seconds", 0.0)),
                format_rank(record.get("rank", 0)),
                total_rank_str,
                record.get("created_at", ""),
                grade,
                record.get("remark", "") or "",
            ),
            tags=tags,
        )
    if existing_selection:
        try:
            tree.selection_set(existing_selection)
        except Exception:
            pass

    compute_today_total(app)


def on_history_right_click(app, event):
    tree = app.competition_history_tree
    row_id = tree.identify_row(event.y)
    if not row_id:
        return
    tree.selection_set(row_id)
    try:
        app.competition_history_menu.tk_popup(event.x_root, event.y_root)
    finally:
        app.competition_history_menu.grab_release()


def on_history_double_click(app, event):
    tree = app.competition_history_tree
    row_id = tree.identify_row(event.y)
    if not row_id:
        return
    all_records = app.competition_service._load()
    target = None
    for r in all_records:
        if r.get("id") == row_id:
            target = r
            break
    if target is None:
        return
    splits = target.get("splits")
    if not splits or not isinstance(splits, list) or len(splits) == 0:
        return
    _show_split_popup(app, target, splits)


def _show_split_popup(app, record, splits):
    popup = tk.Toplevel(app.root)
    popup.title(f"分段成绩 - List {record.get('start_group')}-{record.get('end_group')}")
    popup.configure(bg=app.card_color)
    popup.resizable(False, False)
    popup.transient(app.root)
    popup.grab_set()

    n_splits = len(splits)
    total_elapsed = record.get("elapsed_seconds", 0)

    win_w = 440
    win_h = 200 + n_splits * 18
    x = popup.winfo_screenwidth() // 2 - win_w // 2
    y = popup.winfo_screenheight() // 2 - win_h // 2
    popup.geometry(f"{win_w}x{win_h}+{x}+{y}")

    tk.Label(
        popup,
        text=f"List {record.get('start_group')}-{record.get('end_group')}  总用时：{format_elapsed(total_elapsed)}",
        bg=app.card_color,
        fg=app.config.theme_color,
        font=(app.cn_font_family, 14, "bold"),
    ).pack(pady=(16, 6))

    tk.Frame(popup, bg=app.config.theme_color, height=1).pack(fill="x", padx=24, pady=(0, 6))

    # use Text widget for reliable rendering — monospaced font for alignment
    detail_text = tk.Text(
        popup,
        height=n_splits + 2,
        width=60,
        bg=app.card_color,
        fg=app.text_color,
        font=("Consolas", 11),
        bd=0,
        highlightthickness=0,
        wrap="none",
        state="normal",
    )
    detail_text.pack(fill="both", expand=True, padx=24)

    detail_text.tag_configure("header", font=("Consolas", 11, "bold"), foreground=app.config.theme_color)
    detail_text.tag_configure("row", font=("Consolas", 11))

    # column layout: List(10)  split(13)  cumulative(13)  grade(8)
    detail_text.insert("end", f"{'List':<10}{'Split':>13}{'Total':>13}{'Grade':>8}\n", "header")
    detail_text.insert("end", "─" * 46 + "\n")

    cumulative = 0.0
    for sp in splits:
        list_num = sp.get("list")
        seg = sp.get("elapsed_seconds", 0)
        cumulative += seg
        grade = CompetitionService.get_grade(seg, 1)
        label = f"L{list_num}"
        detail_text.insert(
            "end",
            f"{label:<10}{format_elapsed(seg):>13}{format_elapsed(cumulative):>13}{grade:>8}\n",
            "row",
        )

    detail_text.configure(state="disabled")

    tk.Frame(popup, bg=app.config.theme_color, height=1).pack(fill="x", padx=24, pady=(6, 4))

    avg_elapsed = total_elapsed / max(n_splits, 1)
    grade = CompetitionService.get_grade(total_elapsed, record.get("group_count", n_splits))
    tk.Label(
        popup,
        text=f"平均每组：{format_elapsed(avg_elapsed)}    等级：{grade}",
        bg=app.card_color,
        fg=app.text_secondary,
        font=(app.cn_font_family, 11),
    ).pack()

    ttk.Button(popup, text="关闭", command=popup.destroy).pack(pady=(6, 14))


def delete_selected_record(app):
    tree = app.competition_history_tree
    selection = tree.selection()
    if not selection:
        return
    record_id = selection[0]
    confirm = messagebox.askyesno("删除记录", "确定要删除这条竞赛记录吗？")
    if not confirm:
        return
    if app.competition_service.delete_record(record_id):
        if app.competition_last_record_id == record_id:
            app.competition_last_record_id = ""
            clear_result_labels(app)
            app.competition_invalid_button.configure(state="disabled")
        refresh_history(app)
        app.competition_status_var.set("已删除该条竞赛记录")
    else:
        app.competition_status_var.set("未找到对应记录")


def start_stopwatch(app):
    if app.competition_running:
        return
    app.competition_running = True
    app.competition_start_ts = time.monotonic()
    app.competition_stopwatch_var.set(format_elapsed(0.0))
    gc = app.competition_group_count_int
    if gc > 1:
        app.competition_split_mode = True
        app.competition_current_split = 0
        app.competition_split_elapsed_list = []
        app.competition_split_last_ts = app.competition_start_ts
        app.competition_hint_var.set(f"分段竞赛 | List {app.competition_start_group_int} 进行中... 按下空格记录分段 (1/{gc})")
        app.competition_status_var.set("分段计时开始")
    else:
        app.competition_split_mode = False
        app.competition_hint_var.set("竞赛进行中...再次按下空格键结束计时")
        app.competition_status_var.set("计时开始")
    _tick_stopwatch(app)


def _tick_stopwatch(app):
    if not app.competition_running:
        return
    elapsed = time.monotonic() - app.competition_start_ts
    app.competition_stopwatch_var.set(format_elapsed(elapsed))
    app.competition_stopwatch_job = app.root.after(50, lambda: _tick_stopwatch(app))


def _record_split(app):
    now = time.monotonic()
    split_elapsed = now - app.competition_split_last_ts
    app.competition_split_last_ts = now
    app.competition_split_elapsed_list.append(split_elapsed)
    app.competition_current_split += 1
    gc = app.competition_group_count_int
    sg = app.competition_start_group_int
    current_list = sg + app.competition_current_split - 1
    if app.competition_current_split < gc:
        next_list = sg + app.competition_current_split
        app.competition_hint_var.set(
            f"List {current_list} 已记录 → List {next_list} 进行中... ({app.competition_current_split + 1}/{gc})"
        )
    else:
        app.competition_hint_var.set(
            f"List {current_list} 已记录 → 再按一次空格结束并保存总成绩"
        )


def _finish_split_competition(app):
    app.competition_running = False
    if app.competition_stopwatch_job is not None:
        try:
            app.root.after_cancel(app.competition_stopwatch_job)
        except Exception:
            pass
        app.competition_stopwatch_job = None
    total_elapsed = sum(app.competition_split_elapsed_list)
    app.competition_stopwatch_var.set(format_elapsed(total_elapsed))
    record = app.competition_service.add_record_with_splits(
        app.competition_group_count_int,
        app.competition_start_group_int,
        app.competition_split_elapsed_list,
    )
    app.competition_last_record_id = record.get("id", "")
    populate_result_labels(app, record)
    refresh_history(app)
    compute_today_total(app)
    gc = app.competition_group_count_int
    app.competition_hint_var.set(f"分段竞赛完成 ({gc} 组分段已保存)。按空格键开始新的一轮。")
    show_random_tip(app)
    app.competition_invalid_button.configure(state="normal")


def stop_stopwatch(app):
    if not app.competition_running:
        return
    app.competition_running = False
    if app.competition_stopwatch_job is not None:
        try:
            app.root.after_cancel(app.competition_stopwatch_job)
        except Exception:
            pass
        app.competition_stopwatch_job = None
    elapsed = time.monotonic() - app.competition_start_ts
    app.competition_stopwatch_var.set(format_elapsed(elapsed))
    record = app.competition_service.add_record(
        app.competition_group_count_int,
        app.competition_start_group_int,
        elapsed,
    )
    app.competition_last_record_id = record.get("id", "")
    populate_result_labels(app, record)
    refresh_history(app)
    compute_today_total(app)
    app.competition_hint_var.set("本次成绩已保存。按空格键开始新的一轮。")
    show_random_tip(app)
    app.competition_invalid_button.configure(state="normal")


def on_space_pressed(app, _event=None):
    if not hasattr(app, "competition_page") or not app.competition_page.winfo_ismapped():
        return
    if app.competition_running:
        if getattr(app, "competition_split_mode", False):
            _record_split(app)
            if app.competition_current_split >= app.competition_group_count_int:
                _finish_split_competition(app)
        else:
            stop_stopwatch(app)
    else:
        start_stopwatch(app)


def invalidate_last_record(app):
    if not app.competition_last_record_id:
        return
    confirm = messagebox.askyesno("成绩无效", "确定要作废本次竞赛成绩吗？")
    if not confirm:
        return
    if app.competition_service.delete_record(app.competition_last_record_id):
        app.competition_status_var.set("已作废本次成绩")
    else:
        app.competition_status_var.set("未找到对应记录")
    app.competition_last_record_id = ""
    clear_result_labels(app)
    app.competition_stopwatch_var.set(format_elapsed(0.0))
    app.competition_hint_var.set("按下空格键开始新的一轮竞赛。")
    app.competition_invalid_button.configure(state="disabled")
    refresh_history(app)


def export_excel(app):
    default_name = f"竞赛记录_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = filedialog.asksaveasfilename(
        title="导出竞赛数据",
        defaultextension=".xlsx",
        filetypes=[("Excel 文件", "*.xlsx"), ("全部文件", "*.*")],
        initialfile=default_name,
    )
    if not path:
        return
    try:
        count = app.competition_service.export_to_excel(path)
    except Exception as e:
        messagebox.showerror("导出失败", str(e))
        app.competition_status_var.set(f"导出失败：{e}")
        return
    app.competition_status_var.set(f"已导出 {count} 条记录 → {path}")


def initialize_state(app):
    app.competition_running = False
    app.competition_start_ts = 0.0
    app.competition_stopwatch_job = None
    app.competition_last_record_id = ""
    app.competition_history_records = []
    app.competition_split_mode = False
    app.competition_current_split = 0
    app.competition_split_elapsed_list = []
    app.competition_split_last_ts = 0.0
    app.competition_group_count_var.set("1")
    app.competition_start_group_var.set("1")
    count, start = clamp_start_group("1", "1")
    app.competition_group_count_int = count
    app.competition_start_group_int = start
    update_range_label(app)
    app.competition_stopwatch_var.set(format_elapsed(0.0))
    clear_result_labels(app)
    if hasattr(app, "competition_filter_var"):
        app.competition_filter_var.set(False)
    if hasattr(app, "competition_group_count_filter_var"):
        app.competition_group_count_filter_var.set(True)
    if hasattr(app, "competition_highlight_same_group_var"):
        app.competition_highlight_same_group_var.set(False)
    if hasattr(app, "competition_today_only_var"):
        app.competition_today_only_var.set(False)


def enter_competition_page(app):
    initialize_state(app)
    refresh_history(app)
    app.competition_invalid_button.configure(state="disabled")
    app.competition_hint_var.set("点击界面后按下空格键开始计时，再次按空格键停止并保存成绩。")
    app.competition_status_var.set("")
    compute_today_total(app)
    try:
        app.competition_page.focus_set()
    except Exception:
        pass


def leave_competition_page(app):
    if app.competition_running:
        if app.competition_stopwatch_job is not None:
            try:
                app.root.after_cancel(app.competition_stopwatch_job)
            except Exception:
                pass
            app.competition_stopwatch_job = None
        app.competition_running = False


_COUNT_OPTIONS = (1, 5, 10, 25, 50)


def on_key_press(app, key):
    if not hasattr(app, "competition_page") or not app.competition_page.winfo_ismapped():
        return
    if app.competition_running:
        return
    if key == "w":
        idx = _COUNT_OPTIONS.index(app.competition_group_count_int) if app.competition_group_count_int in _COUNT_OPTIONS else 0
        new_idx = (idx + 1) % len(_COUNT_OPTIONS)
        app.competition_group_count_var.set(str(_COUNT_OPTIONS[new_idx]))
        on_count_change(app)
    elif key == "s":
        idx = _COUNT_OPTIONS.index(app.competition_group_count_int) if app.competition_group_count_int in _COUNT_OPTIONS else 0
        new_idx = (idx - 1) % len(_COUNT_OPTIONS)
        app.competition_group_count_var.set(str(_COUNT_OPTIONS[new_idx]))
        on_count_change(app)
    elif key == "j":
        step = app.competition_group_count_int
        new_start = max(1, app.competition_start_group_int - step)
        # snap to valid step
        if new_start > 1 and step > 1:
            offset = new_start - 1
            snapped_offset = (offset // step) * step
            new_start = 1 + snapped_offset
        app.competition_start_group_var.set(str(new_start))
        on_start_change(app)
    elif key == "k":
        step = app.competition_group_count_int
        count_int, new_start = clamp_start_group(
            app.competition_group_count_var.get(), app.competition_start_group_int + step
        )
        app.competition_start_group_var.set(str(new_start))
        app.competition_group_count_int = count_int
        app.competition_start_group_int = new_start
        update_range_label(app)
        refresh_history(app)


def show_competition_history_popup(app):
    """Show a popup table with daily Date, Total, Review history."""
    from collections import defaultdict
    from tkinter import ttk

    all_records = app.competition_service._load()
    # aggregate by date (only non-split records)
    daily_data = defaultdict(lambda: {"total_seconds": 0.0, "review_lists": 0})
    for r in all_records:
        if r.get("is_split"):
            continue
        date_str = r.get("created_at", "")
        daily_data[date_str]["total_seconds"] += r.get("elapsed_seconds", 0.0)
        daily_data[date_str]["review_lists"] += r.get("group_count", 0)

    def _parse_date(date_str):
        try:
            parts = date_str.split("/")
            return tuple(int(p) for p in parts)
        except Exception:
            return (0, 0, 0)

    sorted_dates = sorted(daily_data.keys(), key=_parse_date, reverse=True)

    popup = tk.Toplevel(app.root)
    popup.title("历史记录总览")
    popup.configure(bg=app.card_color)
    popup.resizable(False, False)
    popup.transient(app.root)
    popup.grab_set()

    win_w = 420
    win_h = 40 + len(sorted_dates) * 28
    win_h = max(200, min(win_h, 560))
    x = popup.winfo_screenwidth() // 2 - win_w // 2
    y = popup.winfo_screenheight() // 2 - win_h // 2
    popup.geometry(f"{win_w}x{win_h}+{x}+{y}")

    columns = ("date", "total", "review")
    tree = ttk.Treeview(popup, columns=columns, show="headings", height=min(len(sorted_dates), 18))
    tree.heading("date", text="日期")
    tree.heading("total", text="Total")
    tree.heading("review", text="Review")
    tree.column("date", width=140, anchor="center")
    tree.column("total", width=120, anchor="center")
    tree.column("review", width=120, anchor="center")

    scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(16, 0))
    scrollbar.pack(side="left", fill="y", pady=(16, 0))

    for date_str in sorted_dates:
        data = daily_data[date_str]
        total_str = format_elapsed(data["total_seconds"])
        review_str = f"{data['review_lists'] * 30} 词"
        tree.insert("", "end", values=(date_str, total_str, review_str))

    ttk.Button(popup, text="关闭", command=popup.destroy).pack(pady=(10, 14))

import json
import ast
import os
import random
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import re
import webbrowser
from datetime import datetime
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from pages.add import build_add_page
from pages.competition import build_competition_page
from pages.home import build_home_page, build_lookup_page
from pages.settings import build_settings_page
from pages.study import build_study_page
from pages import add_actions, competition_actions, study_actions
from services.competition_service import CompetitionService
from services.tips_service import TipsService
from services.database import DictionaryService as DatabaseService
from services.account_service import AccountService
from services.pronunciation_service import PronunciationService
from services.translation_service import SentenceTranslationService
from services.update_service import UpdateService
from app_version import APP_VERSION, GITHUB_REPO


def _resource_path(relative):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


def _data_path(relative):
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = _data_path("vocabulary.db")
SOURCE_DB_PATH = _data_path("stardict.db")
CSV_PATH = _data_path("stardict.csv")
CONFIG_PATH = _data_path("ui_config.json")
ENV_PATH = _data_path(".env")
HISTORY_DIR = _data_path("study_stories")
COMPETITION_DATA_PATH = _data_path("competition_records.json")
LOOKUP_STATS_PATH = _data_path("lookup_stats.json")
PRONUNCIATION_CACHE_DIR = _data_path("pronunciation_cache")
TIPS_PATH = _resource_path("tips.txt")
TIP_PREFIX = "tip："
TIP_TYPEWRITER_MS = 20
TRANSITION_MIN_MS = 1200
TRANSITION_MAX_MS = 1500
DEFAULT_COLOR = "#4f46e5"
ASSETS_DIR = _resource_path("assets")
DEFAULT_BASE_URL = "https://api.openai.com/v1"
CN_FONT_CANDIDATES = ("华文行楷", "STXingkai", "楷体", "Microsoft YaHei")
EN_FONT_CANDIDATES = ("Comic Sans MS", "Segoe UI", "Arial")
CN_COMMON_FONTS = ("华文行楷", "楷体", "微软雅黑", "宋体", "黑体")
EN_COMMON_FONTS = ("Comic Sans MS", "Segoe UI", "Arial", "Times New Roman", "Calibri")
LEGACY_STORY_PROMPT = """Role: 你是一位富有创意的教育家和讲故事高手。
Task: 我将为你提供一份单词表（包含英文单词和中文含义）。请你编写一个逻辑通顺、生动有趣的英文故事，将这些单词全部串联起来。
Rules:
1) 故事全文使用英文。
2) 不要在单词列表里加入 Linger 或 Hyacinth。
3) 每个目标单词在故事中只出现一次，并且要加粗。
4) 每个目标单词后面紧跟编号括号，格式为 (1)、(2)、(3)...，编号连续且不重复。
5) 严禁在故事正文中写出中文含义。
6) 故事总长度控制在“单词数 × 15”个英文词左右，避免过长。"""
DEFAULT_STORY_PROMPT = """Role: 你是一位富有创意的教育家和讲故事高手。
Task: 我将为你提供一份单词表（包含英文单词和中文含义）。请你编写一个逻辑通顺、生动有趣的英文故事，将这些单词全部串联起来。
Character Setting: 故事中必须包含两个主角：小月牙（Hyacinth）和灵儿（Linger），但是这两个名字不在单词表中，不需要考核。他们是一对好朋友。
Formatting Rules:
故事全文使用英文编写。
单词表中的目标单词在故事中出现时，必须加粗。
单词表中的每一个单词在故事中出现且仅出现一次。
在每一个加粗的单词后面，紧跟一个带空格的括号（  1  ），括号内标号1 2 3……
严禁在故事正文中直接写出中文含义。"""


class AppConfig:
    def __init__(self, path):
        self.path = path
        self.theme_color = DEFAULT_COLOR
        self.theme_mode = "day"
        self.font_size = "normal"
        self.cn_font = ""
        self.en_font = ""
        self.story_prompt = DEFAULT_STORY_PROMPT
        self.study_word_count = 10
        self.study_difficulty = "normal"
        self.highlight_learning_words = True
        self.learning_highlight_color = "#fff4b8"
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            color = data.get("theme_color")
            if isinstance(color, str) and color:
                self.theme_color = color
            mode = data.get("theme_mode")
            if mode in ("day", "night"):
                self.theme_mode = mode
            size = data.get("font_size")
            if size in ("normal", "large", "xlarge"):
                self.font_size = size
            cn_font = data.get("cn_font")
            if isinstance(cn_font, str):
                self.cn_font = cn_font
            en_font = data.get("en_font")
            if isinstance(en_font, str):
                self.en_font = en_font
            story_prompt = data.get("story_prompt")
            if isinstance(story_prompt, str) and story_prompt.strip():
                self.story_prompt = story_prompt
            if self.story_prompt.strip() == LEGACY_STORY_PROMPT.strip():
                self.story_prompt = DEFAULT_STORY_PROMPT
            study_word_count = data.get("study_word_count")
            if isinstance(study_word_count, int) and 5 <= study_word_count <= 20:
                self.study_word_count = study_word_count
            study_difficulty = data.get("study_difficulty")
            if study_difficulty in ("easy", "normal", "hard"):
                self.study_difficulty = study_difficulty
            highlight_learning_words = data.get("highlight_learning_words")
            if isinstance(highlight_learning_words, bool):
                self.highlight_learning_words = highlight_learning_words
            learning_highlight_color = data.get("learning_highlight_color")
            if isinstance(learning_highlight_color, str) and re.match(r"^#[0-9a-fA-F]{6}$", learning_highlight_color):
                self.learning_highlight_color = learning_highlight_color
        except Exception:
            self.theme_color = DEFAULT_COLOR

    def save(self):
        data = {
            "theme_color": self.theme_color,
            "theme_mode": self.theme_mode,
            "font_size": self.font_size,
            "cn_font": self.cn_font,
            "en_font": self.en_font,
            "story_prompt": self.story_prompt,
            "study_word_count": self.study_word_count,
            "study_difficulty": self.study_difficulty,
            "highlight_learning_words": self.highlight_learning_words,
            "learning_highlight_color": self.learning_highlight_color,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def mix_color(color_hex, bg_hex, ratio):
    color_hex = color_hex.lstrip("#")
    bg_hex = bg_hex.lstrip("#")
    r1, g1, b1 = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
    r2, g2, b2 = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
    r = int(r1 * (1 - ratio) + r2 * ratio)
    g = int(g1 * (1 - ratio) + g2 * ratio)
    b = int(b1 * (1 - ratio) + b2 * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


class RoundedTag(tk.Canvas):
    def __init__(self, master, text, text_font, bg, fg, fill, outline, radius=16, padx=18, pady=8):
        self.text = text
        self.text_font = text_font
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self.fill = fill
        self.outline = outline
        self.fg = fg
        font_obj = tkfont.Font(font=text_font)
        width = font_obj.measure(text) + padx * 2
        height = font_obj.metrics("linespace") + pady * 2
        super().__init__(master, width=width, height=height, bg=bg, bd=0, highlightthickness=0)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        r = min(self.radius, w // 2, h // 2)
        self.create_arc(0, 0, r * 2, r * 2, start=90, extent=90, fill=self.fill, outline=self.fill)
        self.create_arc(w - r * 2, 0, w, r * 2, start=0, extent=90, fill=self.fill, outline=self.fill)
        self.create_arc(w - r * 2, h - r * 2, w, h, start=270, extent=90, fill=self.fill, outline=self.fill)
        self.create_arc(0, h - r * 2, r * 2, h, start=180, extent=90, fill=self.fill, outline=self.fill)
        self.create_rectangle(r, 0, w - r, h, fill=self.fill, outline=self.fill)
        self.create_rectangle(0, r, w, h - r, fill=self.fill, outline=self.fill)
        self.create_arc(0, 0, r * 2, r * 2, start=90, extent=90, style="arc", outline=self.outline, width=2)
        self.create_arc(w - r * 2, 0, w, r * 2, start=0, extent=90, style="arc", outline=self.outline, width=2)
        self.create_arc(w - r * 2, h - r * 2, w, h, start=270, extent=90, style="arc", outline=self.outline, width=2)
        self.create_arc(0, h - r * 2, r * 2, h, start=180, extent=90, style="arc", outline=self.outline, width=2)
        self.create_line(r, 1, w - r, 1, fill=self.outline, width=2)
        self.create_line(r, h - 1, w - r, h - 1, fill=self.outline, width=2)
        self.create_line(1, r, 1, h - r, fill=self.outline, width=2)
        self.create_line(w - 1, r, w - 1, h - r, fill=self.outline, width=2)
        self.create_text(w // 2, h // 2, text=self.text, font=self.text_font, fill=self.fg)

    def apply_theme(self, fg, fill, outline, bg):
        self.fg = fg
        self.fill = fill
        self.outline = outline
        self.configure(bg=bg)
        self._draw()

    def set_text(self, text):
        self.text = text
        font_obj = tkfont.Font(font=self.text_font)
        width = font_obj.measure(text) + self.padx * 2
        self.configure(width=width)
        self._draw()

    def set_font(self, text_font):
        self.text_font = text_font
        font_obj = tkfont.Font(font=self.text_font)
        width = font_obj.measure(self.text) + self.padx * 2
        self.configure(width=width)
        self._draw()


class IconTile(tk.Frame):
    def __init__(self, master, image_frames, bg, card_bg, border_color, click_command=None):
        super().__init__(master, bg=bg)
        self.image_frames = image_frames
        self.click_command = click_command
        self.base_index = 0
        self.current_index = self.base_index
        self.target_index = self.base_index
        self.pending_animation = None
        self.card = tk.Frame(self, bg=bg, highlightthickness=0, bd=0, padx=0, pady=0)
        self.card.pack()
        self.label = tk.Label(self.card, image=self.image_frames[self.current_index], bg=bg, bd=0, cursor="hand2")
        self.label.pack()
        for widget in (self, self.card, self.label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def apply_theme(self, bg, card_bg, border_color):
        self.configure(bg=bg)
        self.card.configure(bg=bg)
        self.label.configure(bg=bg)

    def _on_enter(self, _event):
        self.target_index = len(self.image_frames) - 1
        self._start_animation()

    def _on_leave(self, _event):
        self.target_index = self.base_index
        self._start_animation()

    def _start_animation(self):
        if self.pending_animation is not None:
            self.after_cancel(self.pending_animation)
        self.pending_animation = self.after(12, self._animate_step)

    def _animate_step(self):
        if self.current_index < self.target_index:
            self.current_index += 1
        elif self.current_index > self.target_index:
            self.current_index -= 1
        self.label.configure(image=self.image_frames[self.current_index])
        if self.current_index == self.target_index:
            self.pending_animation = None
            return
        self.pending_animation = self.after(12, self._animate_step)

    def _on_click(self, _event):
        if self.click_command:
            self.click_command()


class VocabularyApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"铃兰词典 v{APP_VERSION}")
        self.root.geometry("940x680")
        self.root.minsize(860, 620)
        self.bg_color = "#f7f6ef"
        self.card_color = "#fffdf8"
        self.text_color = "#2f2d26"
        self.text_secondary = "#4d4a3f"
        self.surface_mix_base = "#ffffff"
        self.overlay_mix_base = "#ffffff"
        self.button_mix_base = "#ffffff"
        self.tag_mix_base = "#ffffff"
        self.tag_fill_ratio = 0.88
        self.title_fill_ratio = 0.85
        self.search_fill_ratio = 0.86
        self.list_tag_fill_ratio = 0.9
        self.result_mix_ratio = 0.93
        self.list_mix_ratio = 0.94
        self.prompt_mix_ratio = 0.92
        self.overlay_mix_ratio = 0.65
        self.button_mix_ratio = 0.2
        self.button_active_ratio = 0.1

        self.config = AppConfig(CONFIG_PATH)
        self.mode_var = tk.StringVar(value="")
        self._apply_theme_mode()
        self.dictionary_service = DatabaseService(DB_PATH, SOURCE_DB_PATH, CSV_PATH)
        self.account_service = AccountService(DB_PATH, HISTORY_DIR)
        self.translation_service = SentenceTranslationService(from_code="en", to_code="zh")
        self.pronunciation_service = PronunciationService(PRONUNCIATION_CACHE_DIR)
        self.competition_service = CompetitionService(COMPETITION_DATA_PATH)
        self.update_service = UpdateService(GITHUB_REPO, APP_VERSION)
        self.tips_service = TipsService(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "tips.txt"),
            os.path.dirname(os.path.abspath(__file__)),
        )
        self.lookup_stats = self._load_lookup_stats()
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.dotenv_enabled = load_dotenv is not None
        self._load_env_settings()
        try:
            self.available_fonts = set(tkfont.families())
        except Exception:
            self.available_fonts = set()
        self.cn_font_family = self._resolve_font_family(self.config.cn_font, CN_FONT_CANDIDATES)
        self.en_font_family = self._resolve_font_family(self.config.en_font, EN_FONT_CANDIDATES)

        self.theme_var = tk.StringVar(value=f"主题色：{self.config.theme_color}")
        self.font_size_var = tk.StringVar(value=self.config.font_size)
        self.api_key_var = tk.StringVar(value=self.api_key)
        self.base_url_var = tk.StringVar(value=self.base_url)
        self.cn_font_var = tk.StringVar(value=self.cn_font_family)
        self.en_font_var = tk.StringVar(value=self.en_font_family)
        self.story_prompt_var = tk.StringVar(value=self.config.story_prompt)
        self.study_word_count_var = tk.IntVar(value=self.config.study_word_count)
        self.study_difficulty_var = tk.StringVar(value=self.config.study_difficulty)
        self.highlight_learning_words_var = tk.BooleanVar(value=self.config.highlight_learning_words)
        self.learning_highlight_color_var = tk.StringVar(value=self.config.learning_highlight_color)
        self.update_status_var = tk.StringVar(value="当前版本：v%s" % APP_VERSION)
        self.search_word_var = tk.StringVar(value="")
        self.lookup_word_var = tk.StringVar(value="")
        self.lookup_stats_var = tk.StringVar(value=self._format_lookup_stats())
        self.add_word_var = tk.StringVar(value="")
        self.import_file_var = tk.StringVar(value="")
        self.add_status_var = tk.StringVar(value="")
        self.study_status_var = tk.StringVar(value="")
        self.quick_lookup_var = tk.StringVar(value="")
        self.quick_lookup_result_var = tk.StringVar(value="")
        self.quick_lookup_result_var.trace_add("write", self._on_quick_lookup_result_var_change)
        self.search_word_var.trace_add("write", self._on_search_word_var_change)
        self.lookup_word_var.trace_add("write", self._on_lookup_word_var_change)
        self.competition_group_count_var = tk.StringVar(value="1")
        self.competition_start_group_var = tk.StringVar(value="1")
        self.competition_range_var = tk.StringVar(value="→ List 1-1")
        self.competition_stopwatch_var = tk.StringVar(value="00:00.000")
        self.competition_hint_var = tk.StringVar(value="按下空格键开始竞赛计时。")
        self.competition_status_var = tk.StringVar(value="")
        self.competition_today_total_var = tk.StringVar(value="Total：00:00.000")
        self.competition_review_var = tk.StringVar(value="Review: 0 Lists")
        self.competition_group_count_filter_var = tk.BooleanVar(value=True)
        self.competition_highlight_same_group_var = tk.BooleanVar(value=False)
        self.competition_today_only_var = tk.BooleanVar(value=False)
        self.competition_group_count_int = 1
        self.competition_start_group_int = 1
        self.competition_running = False
        self.competition_start_ts = 0.0
        self.competition_stopwatch_job = None
        self.competition_last_record_id = ""
        self.competition_history_records = []
        self.competition_split_mode = False
        self.competition_current_split = 0
        self.competition_split_elapsed_list = []
        self.competition_split_last_ts = 0.0
        self.icon_tiles = []
        self.icon_images = {}
        self.separator_image = None
        self.corner_images = []
        self.corner_labels = []
        self.initialized = False
        self.transition_running = False
        self.home_lookup_job = None
        self.full_lookup_job = None
        self.lookup_history_items = []
        self.current_quiz_words = []
        self.current_quiz_word_set = set()
        self.answer_entries = []
        self.answer_result_labels = []
        self.answer_blocks = []
        self.current_story_plain = ""
        self.current_story_md_path = ""
        self.story_text_fonts = {}
        self.study_history_window = None
        self.story_request_seq = 0
        self.active_story_request_id = 0
        self.review_request_seq = 0
        self.active_review_request_id = 0
        self.study_loading_running = False
        self.study_loading_job = None
        self.study_loading_tick = 0
        self.study_loading_base_message = ""
        self.startup_loading_running = False
        self.startup_loading_job = None
        self.startup_loading_tick = 0
        self.startup_loading_base_message = ""
        self.translation_preload_error = ""
        self.update_check_running = False
        self.update_auto_checked = False
        self.latest_release_info = {}
        self.loading_tips = self._load_loading_tips()
        self.last_loading_tip = ""
        self.last_home_tip = ""
        self.tip_typewriter_jobs = {}
        self.RoundedTag = RoundedTag
        self.mix_color = mix_color
        self.CN_COMMON_FONTS = CN_COMMON_FONTS
        self.EN_COMMON_FONTS = EN_COMMON_FONTS

        self._build_ui()
        self._warn_if_text_corruption()
        self._apply_theme(self.config.theme_color)
        self._apply_font_size()
        self._apply_learning_word_highlight_settings()
        self.root.after(120, self._start_initialize)

    def _load_env_settings(self):
        env_path = ENV_PATH
        if load_dotenv is not None:
            load_dotenv(dotenv_path=env_path, override=True)
            api_key = os.getenv("API_KEY")
            base_url = os.getenv("BASE_URL")
        else:
            api_key, base_url = self._read_env_file(env_path)
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url + "/v1"

    def _read_env_file(self, env_path):
        if not os.path.exists(env_path):
            return "", DEFAULT_BASE_URL
        api_key = ""
        base_url = DEFAULT_BASE_URL
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, value = text.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "API_KEY":
                    api_key = value
                elif key == "BASE_URL":
                    base_url = value
        return api_key, base_url

    def _refresh_env_labels(self):
        if hasattr(self, "api_key_var"):
            self.api_key_var.set(self.api_key)
        if hasattr(self, "base_url_var"):
            self.base_url_var.set(self.base_url)

    def _today_lookup_key(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _load_lookup_stats(self):
        try:
            with open(LOOKUP_STATS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        total = data.get("total_count", 0)
        try:
            total = int(total)
        except Exception:
            total = 0
        daily_counts = data.get("daily_counts")
        if not isinstance(daily_counts, dict):
            daily_counts = {}
        history = data.get("history")
        if not isinstance(history, list):
            history = []
        return {
            "total_count": max(0, total),
            "daily_counts": daily_counts,
            "history": history[:80],
        }

    def _save_lookup_stats(self):
        data = dict(getattr(self, "lookup_stats", {}) or {})
        data["history"] = (data.get("history") or [])[:80]
        with open(LOOKUP_STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _format_lookup_stats(self):
        data = getattr(self, "lookup_stats", {}) or {}
        today = self._today_lookup_key()
        daily_counts = data.get("daily_counts") or {}
        today_count = daily_counts.get(today, 0)
        try:
            today_count = int(today_count)
        except Exception:
            today_count = 0
        total_count = data.get("total_count", 0)
        try:
            total_count = int(total_count)
        except Exception:
            total_count = 0
        return f"Total 查询：{total_count}    今日查询：{today_count}"

    def _refresh_lookup_stats_view(self):
        if hasattr(self, "lookup_stats_var"):
            self.lookup_stats_var.set(self._format_lookup_stats())
        self._refresh_lookup_history_view()

    def _word_core_translation(self, translation):
        text = (translation or "").strip()
        if not text:
            return "暂无中文释义"
        first_line = text.splitlines()[0].strip()
        parts = re.split(r"[；;。]", first_line, maxsplit=1)
        return (parts[0] or first_line).strip() or "暂无中文释义"

    def _format_word_detail(self, result):
        if not result:
            return ""
        word = result.get("word") or ""
        phonetic = result.get("phonetic") or ""
        pos = result.get("pos") or ""
        definition = result.get("definition") or ""
        translation = result.get("translation") or ""
        lines = [f"单词：{word}"]
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
        return "\n".join(lines)

    def _format_history_item(self, item):
        word = (item.get("word") or item.get("query") or "").strip()
        phonetic = (item.get("phonetic") or "").strip()
        core = (item.get("core_translation") or "").strip()
        phonetic_part = f" [{phonetic}]" if phonetic else ""
        return f"{word}{phonetic_part}  {core}".strip()

    def _refresh_lookup_history_view(self):
        if not hasattr(self, "lookup_history_listbox"):
            return
        self.lookup_history_listbox.delete(0, tk.END)
        history = (getattr(self, "lookup_stats", {}) or {}).get("history") or []
        self.lookup_history_items = history
        for item in history:
            self.lookup_history_listbox.insert(tk.END, self._format_history_item(item))

    def _resolve_font_family(self, preferred, candidates):
        if preferred and (not self.available_fonts or preferred in self.available_fonts):
            return preferred
        for family in candidates:
            if not self.available_fonts or family in self.available_fonts:
                return family
        return preferred or candidates[0]


    def _warn_if_text_corruption(self):
        files = [
            os.path.join(BASE_DIR, "pages", "study.py"),
            os.path.join(BASE_DIR, "pages", "study_actions.py"),
            os.path.join(BASE_DIR, "pages", "add_actions.py"),
        ]
        issues = []
        for file_path in files:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
            except Exception as e:
                issues.append((os.path.basename(file_path), f"Parse failed: {e}"))
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if "???" in node.value:
                        issues.append((os.path.basename(file_path), f"line {getattr(node, 'lineno', '?')} has suspicious text"))
                        break
        if issues:
            preview = "\n".join([f"{name}: {msg}" for name, msg in issues[:6]])
            messagebox.showwarning(
                "Text Integrity Check",
                "Potential text corruption detected (e.g. ???).\n\n"
                + preview
                + "\n\nPlease run: python tools/check_text_integrity.py",
            )

    def _load_loading_tips(self):
        if hasattr(self, "tips_service"):
            return self.tips_service._load_tips()
        default_tips = ["每背会一个单词，都会离目标更近一步。"]
        if not os.path.exists(TIPS_PATH):
            return default_tips
        text = None
        for encoding in ("utf-8", "utf-8-sig", "gbk", "utf-16"):
            try:
                with open(TIPS_PATH, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except Exception:
                continue
        if text is None:
            return default_tips
        tips = [line.strip() for line in text.splitlines() if line.strip()]
        return tips or default_tips

    def _normalize_tip_text(self, raw_tip):
        tip_text = (raw_tip or "").strip()
        if not tip_text:
            tip_text = "每背会一个单词，都会离目标更近一步。"
        return re.sub(r"^\s*tip[:：]\s*", "", tip_text, flags=re.IGNORECASE)

    def _format_loading_tip(self, raw_tip):
        tip_text = self._normalize_tip_text(raw_tip)
        return f"{TIP_PREFIX}{tip_text}"

    def _pick_loading_tip(self):
        # Reload tips every time so newly added lines in tips.txt can be used immediately.
        self.loading_tips = self._load_loading_tips()
        tips = self.loading_tips or ["每背会一个单词，都会离目标更近一步。"]
        if len(tips) == 1:
            raw_tip = tips[0]
            self.last_loading_tip = raw_tip
            if hasattr(self, "tips_service"):
                self.tips_service.mark_seen(raw_tip)
            return self._format_loading_tip(raw_tip)
        candidates = [tip for tip in tips if tip != self.last_loading_tip]
        raw_tip = random.choice(candidates or tips)
        self.last_loading_tip = raw_tip
        if hasattr(self, "tips_service"):
            self.tips_service.mark_seen(raw_tip)
        return self._format_loading_tip(raw_tip)

    def _pick_home_tip(self):
        self.loading_tips = self._load_loading_tips()
        tips = self.loading_tips or ["每背会一个单词，都会离目标更近一步。"]
        if len(tips) == 1:
            raw_tip = tips[0]
            self.last_home_tip = raw_tip
            if hasattr(self, "tips_service"):
                self.tips_service.mark_seen(raw_tip)
            return self._normalize_tip_text(raw_tip)
        candidates = [tip for tip in tips if tip != self.last_home_tip]
        raw_tip = random.choice(candidates or tips)
        self.last_home_tip = raw_tip
        if hasattr(self, "tips_service"):
            self.tips_service.mark_seen(raw_tip)
        return self._normalize_tip_text(raw_tip)

    def _tip_var_for_target(self, target):
        mapping = {
            "startup": "startup_loading_tip_var",
            "study": "study_loading_tip_var",
            "transition": "transition_tip_var",
        }
        var_name = mapping.get(target, "")
        return getattr(self, var_name, None) if var_name else None

    def _stop_tip_typewriter(self, target):
        job = self.tip_typewriter_jobs.pop(target, None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

    def _start_tip_typewriter(self, target, tip_text):
        var = self._tip_var_for_target(target)
        if var is None:
            return
        self._stop_tip_typewriter(target)
        full_text = (tip_text or "").strip()
        if not full_text:
            var.set("")
            return
        var.set("")

        def step(index):
            var.set(full_text[:index])
            if index >= len(full_text):
                self.tip_typewriter_jobs.pop(target, None)
                return
            self.tip_typewriter_jobs[target] = self.root.after(
                TIP_TYPEWRITER_MS,
                lambda: step(index + 1),
            )

        step(1)

    def _font_options(self, common_fonts):
        if not self.available_fonts:
            return tuple(common_fonts)
        output = [name for name in common_fonts if name in self.available_fonts]
        if not output:
            output = list(common_fonts)
        return tuple(output)

    def _apply_theme_mode(self):
        mode = self.config.theme_mode if self.config.theme_mode in ("day", "night") else "day"
        if mode == "night":
            self.bg_color = "#171c27"
            self.card_color = "#222a39"
            self.text_color = "#e9eef9"
            self.text_secondary = "#c2ccdf"
            self.surface_mix_base = "#1a2130"
            self.overlay_mix_base = "#141a24"
            self.button_mix_base = "#1f2737"
            self.tag_mix_base = "#1f2737"
            self.tag_fill_ratio = 0.60
            self.title_fill_ratio = 0.56
            self.search_fill_ratio = 0.58
            self.list_tag_fill_ratio = 0.64
            self.result_mix_ratio = 0.8
            self.list_mix_ratio = 0.78
            self.prompt_mix_ratio = 0.78
            self.overlay_mix_ratio = 0.45
            self.button_mix_ratio = 0.28
            self.button_active_ratio = 0.18
            mode_text = "界面模式：夜间模式"
        else:
            self.bg_color = "#f7f6ef"
            self.card_color = "#fffdf8"
            self.text_color = "#2f2d26"
            self.text_secondary = "#4d4a3f"
            self.surface_mix_base = "#ffffff"
            self.overlay_mix_base = "#ffffff"
            self.button_mix_base = "#ffffff"
            self.tag_mix_base = "#ffffff"
            self.tag_fill_ratio = 0.88
            self.title_fill_ratio = 0.85
            self.search_fill_ratio = 0.86
            self.list_tag_fill_ratio = 0.9
            self.result_mix_ratio = 0.93
            self.list_mix_ratio = 0.94
            self.prompt_mix_ratio = 0.92
            self.overlay_mix_ratio = 0.65
            self.button_mix_ratio = 0.2
            self.button_active_ratio = 0.1
            mode_text = "界面模式：日间模式"
        self.root.configure(bg=self.bg_color)
        if hasattr(self, "mode_var"):
            self.mode_var.set(mode_text)

    def _retint_widget_tree(self, root_widget, old_bg, new_bg, old_card, new_card, old_text, new_text, old_secondary, new_secondary):
        queue = [root_widget]
        while queue:
            widget = queue.pop(0)
            queue.extend(widget.winfo_children())
            try:
                bg = widget.cget("bg")
                if bg == old_bg:
                    widget.configure(bg=new_bg)
                elif bg == old_card:
                    widget.configure(bg=new_card)
            except Exception:
                pass
            try:
                fg = widget.cget("fg")
                if fg == old_text:
                    widget.configure(fg=new_text)
                elif fg == old_secondary:
                    widget.configure(fg=new_secondary)
            except Exception:
                pass

    def _set_theme_mode(self, mode):
        if mode not in ("day", "night"):
            return
        if self.config.theme_mode == mode:
            if hasattr(self, "settings_status_var"):
                self.settings_status_var.set("界面模式未变化")
            return
        old_bg = self.bg_color
        old_card = self.card_color
        old_text = self.text_color
        old_secondary = self.text_secondary
        self.config.theme_mode = mode
        self.config.save()
        self._apply_theme_mode()
        self._retint_widget_tree(
            self.root,
            old_bg,
            self.bg_color,
            old_card,
            self.card_color,
            old_text,
            self.text_color,
            old_secondary,
            self.text_secondary,
        )
        if self.study_history_window and self.study_history_window.winfo_exists():
            self._retint_widget_tree(
                self.study_history_window,
                old_bg,
                self.bg_color,
                old_card,
                self.card_color,
                old_text,
                self.text_color,
                old_secondary,
                self.text_secondary,
            )
        self._apply_theme(self.config.theme_color)
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set("已切换为夜间模式" if mode == "night" else "已切换为日间模式")

    def _build_ui(self):
        build_home_page(self)
        self._create_startup_loading_overlay()

        self._load_decorations()
        self._place_corners()
        self.root.bind("<Configure>", self._on_root_resize)
        self._build_add_page()
        self._build_lookup_page()
        self._build_settings_page()
        self._build_study_page()
        self._build_competition_page()
        self.root.bind("<space>", self._on_competition_space)
        self.root.bind_all("<Control-j>", self._play_current_lookup_pronunciation)
        self.root.after(0, self._sync_home_search_width)

    def _build_icons(self):
        self.icon_tiles = []
        icon_items = [
            ("设置.png", self._open_settings_page),
            ("添加.png", self._open_add_page),
            ("学习.png", self._open_study_page),
            ("竞赛.png", self._open_competition_page),
        ]
        for file_name, click_command in icon_items:
            frames = self._create_icon_frames(file_name)
            tile = IconTile(
                self.icons_row,
                image_frames=frames,
                bg=self.bg_color,
                card_bg=self.card_color,
                border_color=self.config.theme_color,
                click_command=click_command,
            )
            tile.pack(side="left", padx=30)
            self.icon_tiles.append(tile)

    def _create_icon_frames(self, file_name):
        path = os.path.join(ASSETS_DIR, file_name)
        try:
            source = tk.PhotoImage(file=path)
        except Exception:
            fallback = tk.PhotoImage(width=180, height=180)
            fallback.put("#d8d8d8", to=(0, 0, 180, 180))
            return [fallback for _ in range(9)]
        zoom_factor = 6
        base_denom = 24
        # Auto-scale so all icons render at a consistent display size (~180px)
        target_width = 180
        src_width = source.width()
        if src_width and src_width > 0:
            ideal_denom = zoom_factor * src_width / target_width
            if ideal_denom > 0:
                base_denom = round(ideal_denom)
        offsets = [1, 1, 0, 0, 0, -1, -1, -1, -1]
        denominators = [max(1, base_denom + o) for o in offsets]
        frames = []
        for denominator in denominators:
            frame = source.zoom(zoom_factor, zoom_factor).subsample(denominator, denominator)
            frames.append(frame)
        self.icon_images[file_name] = [source] + frames
        return frames

    def _load_decorations(self):
        sep_path = os.path.join(ASSETS_DIR, "边框1.png")
        try:
            sep_source = tk.PhotoImage(file=sep_path)
            factor = max(1, round(sep_source.width() / 560))
            self.separator_image = sep_source.subsample(factor, factor)
            self.icon_images["separator"] = [sep_source, self.separator_image]
            self.separator_label.configure(image=self.separator_image)
        except Exception:
            self.separator_label.configure(image="", text="")
        self.corner_images = []
        self.corner_labels = []
        for file_name in ("角框2.png", "角框4.png", "角框3.png", "角框1.png"):
            try:
                source = tk.PhotoImage(file=os.path.join(ASSETS_DIR, file_name))
                factor = max(1, round(source.width() / 150))
                image = source.subsample(factor, factor)
                self.icon_images[f"corner_{file_name}"] = [source, image]
                label = tk.Label(self.root, image=image, bg=self.bg_color, bd=0, highlightthickness=0)
                self.corner_images.append(image)
                self.corner_labels.append(label)
            except Exception:
                continue

    def _place_corners(self):
        if len(self.corner_labels) < 4:
            return
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        margin = 10
        self.corner_labels[0].place(x=margin, y=margin)
        self.corner_labels[1].place(x=w - self.corner_images[1].width() - margin, y=margin)
        self.corner_labels[2].place(x=margin, y=h - self.corner_images[2].height() - margin)
        self.corner_labels[3].place(x=w - self.corner_images[3].width() - margin, y=h - self.corner_images[3].height() - margin)

    def _on_root_resize(self, _event):
        self._place_corners()
        self._sync_home_search_width()

    def _sync_home_search_width(self):
        if not hasattr(self, "search_panel") or not hasattr(self, "icons_row") or not hasattr(self, "container"):
            return
        try:
            container_padx = int(float(self.container.cget("padx")))
        except Exception:
            container_padx = 0
        container_width = self.container.winfo_width()
        if container_width <= 1:
            container_width = max(1, self.root.winfo_width())
        content_width = max(1, container_width - container_padx * 2)
        icons_width = self.icons_row.winfo_width()
        if icons_width <= 1:
            icons_width = self.icons_row.winfo_reqwidth()
        if icons_width <= 1:
            return
        min_search_width = 520
        target_width = max(min_search_width, icons_width)
        max_width = max(min_search_width, content_width - 8)
        target_width = min(target_width, max_width)
        side_pad = max(0, (content_width - target_width) // 2)
        self.search_panel.pack_configure(padx=(side_pad, side_pad))

    def _build_add_page(self):
        build_add_page(self)

    def _build_lookup_page(self):
        build_lookup_page(self)
        self._refresh_lookup_stats_view()

    def _build_settings_page(self):
        build_settings_page(self)

    def _build_study_page(self):
        build_study_page(self)
        self._create_study_loading_overlay()

    def _build_competition_page(self):
        build_competition_page(self)
        competition_actions.initialize_state(self)
        self.root.bind("<w>", self._on_competition_key_w)
        self.root.bind("<s>", self._on_competition_key_s)
        self.root.bind("<j>", self._on_competition_key_j)
        self.root.bind("<k>", self._on_competition_key_k)
        self.root.bind("<Key-1>", self._on_competition_key_toggle_1)
        self.root.bind("<Key-2>", self._on_competition_key_toggle_2)
        self.root.bind("<Key-3>", self._on_competition_key_toggle_3)
        self.root.bind("<Key-4>", self._on_competition_key_toggle_4)

    def _on_competition_count_change(self, _event=None):
        competition_actions.on_count_change(self, _event)

    def _on_competition_start_change(self, _event=None):
        competition_actions.on_start_change(self, _event)

    def _on_competition_history_right_click(self, event):
        competition_actions.on_history_right_click(self, event)

    def _on_competition_history_double_click(self, event):
        competition_actions.on_history_double_click(self, event)

    def _delete_selected_competition_record(self):
        competition_actions.delete_selected_record(self)

    def _export_competition_excel(self):
        competition_actions.export_excel(self)

    def _invalidate_last_competition(self):
        competition_actions.invalidate_last_record(self)

    def _on_competition_space(self, event=None):
        competition_actions.on_space_pressed(self, event)

    def _on_competition_key_w(self, event=None):
        competition_actions.on_key_press(self, "w")

    def _on_competition_key_s(self, event=None):
        competition_actions.on_key_press(self, "s")

    def _on_competition_key_j(self, event=None):
        competition_actions.on_key_press(self, "j")

    def _on_competition_key_k(self, event=None):
        competition_actions.on_key_press(self, "k")

    def _on_competition_key_toggle_1(self, event=None):
        competition_actions.on_key_toggle(self, "1")

    def _on_competition_key_toggle_2(self, event=None):
        competition_actions.on_key_toggle(self, "2")

    def _on_competition_key_toggle_3(self, event=None):
        competition_actions.on_key_toggle(self, "3")

    def _on_competition_key_toggle_4(self, event=None):
        competition_actions.on_key_toggle(self, "4")

    def _on_competition_filter_toggle(self):
        competition_actions.on_filter_toggle(self)

    def _show_competition_history_popup(self):
        competition_actions.show_competition_history_popup(self)

    def _show_tips_gallery(self):
        if not hasattr(self, "tips_service"):
            return
        all_tips = self.tips_service.get_all_tips_status()
        counts = self.tips_service.get_seen_counts()

        popup = tk.Toplevel(self.root)
        popup.title("Tips 图鉴")
        popup.configure(bg=self.card_color)
        popup.resizable(True, True)
        popup.transient(self.root)
        popup.grab_set()

        win_w = 680
        win_h = 620
        x = popup.winfo_screenwidth() // 2 - win_w // 2
        y = popup.winfo_screenheight() // 2 - win_h // 2
        popup.geometry(f"{win_w}x{win_h}+{x}+{y}")

        header = tk.Frame(popup, bg=self.card_color)
        header.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(
            header,
            text=f"Tips 图鉴 — 普通 {counts['normal_seen']}/{counts['normal_total']}  |  特殊 {counts['special_seen']}/{counts['special_total']}",
            bg=self.card_color,
            fg=self.config.theme_color,
            font=(self.cn_font_family, 14, "bold"),
        ).pack(side="left")

        text_frame = tk.Frame(popup, bg=self.card_color)
        text_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        text_area = tk.Text(
            text_frame,
            wrap="word",
            bg=self.card_color,
            fg=self.text_color,
            font=(self.cn_font_family, 11),
            bd=0,
            highlightthickness=0,
            padx=16,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)
        text_area.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_area.tag_configure("seen", foreground=self.text_secondary)
        text_area.tag_configure("unseen", foreground="#999999")
        text_area.tag_configure("special_seen", foreground=self.text_secondary)
        text_area.tag_configure("special_unseen", foreground="#b8a0d0")
        text_area.tag_configure("divider", foreground=self.config.theme_color, font=(self.cn_font_family, 9))

        normal_header_printed = False
        special_header_printed = False

        for tip in all_tips:
            if tip["type"] == "normal":
                if not normal_header_printed:
                    text_area.insert("end", "── 普通 Tips ──\n", "divider")
                    normal_header_printed = True
                if tip["seen"]:
                    text_area.insert("end", f"{tip['text']}\n\n", "seen")
                else:
                    text_area.insert("end", f"???\n\n", "unseen")
            else:
                if not special_header_printed:
                    text_area.insert("end", "\n── 特殊 Tips（彩蛋）──\n", "divider")
                    special_header_printed = True
                if tip["seen"]:
                    text_area.insert("end", f"{tip['text']}\n\n", "special_seen")
                else:
                    hint = tip.get("hint", "")
                    hint_text = f"（{hint}）" if hint else ""
                    text_area.insert("end", f"???{hint_text}\n\n", "special_unseen")

        text_area.configure(state="disabled")

        ttk.Button(popup, text="关闭", command=popup.destroy).pack(pady=(0, 14))

    def _create_study_loading_overlay(self):
        if not hasattr(self, "study_page"):
            return
        overlay_bg = mix_color(self.config.theme_color, self.overlay_mix_base, self.overlay_mix_ratio)
        self.study_loading_overlay = tk.Frame(self.study_page, bg=overlay_bg)
        self.study_loading_box = tk.Frame(self.study_loading_overlay, bg=self.card_color, padx=26, pady=20)
        self.study_loading_box.place(relx=0.5, rely=0.5, anchor="center")
        self.study_loading_icon_var = tk.StringVar(value="(^_^)")
        self.study_loading_text_var = tk.StringVar(value="铃兰正在忙碌中")
        self.study_loading_icon_label = tk.Label(
            self.study_loading_box,
            textvariable=self.study_loading_icon_var,
            bg=self.card_color,
            fg=self.config.theme_color,
            font=(self.en_font_family, 17, "bold"),
        )
        self.study_loading_icon_label.pack(anchor="center", pady=(0, 8))
        self.study_loading_text_label = tk.Label(
            self.study_loading_box,
            textvariable=self.study_loading_text_var,
            bg=self.card_color,
            fg=self.text_secondary,
            font=(self.cn_font_family, 11),
        )
        self.study_loading_text_label.pack(anchor="center", pady=(0, 10))
        self.study_loading_tip_var = tk.StringVar(value="")
        self.study_loading_tip_label = tk.Label(
            self.study_loading_overlay,
            textvariable=self.study_loading_tip_var,
            bg=overlay_bg,
            fg=self.text_secondary,
            font=(self.cn_font_family, 10),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.study_loading_tip_label.place(relx=0.02, rely=0.98, anchor="sw")
        self.study_loading_bar = ttk.Progressbar(
            self.study_loading_box,
            orient="horizontal",
            mode="indeterminate",
            length=220,
        )
        self.study_loading_bar.pack(anchor="center")
        self.study_loading_overlay.place_forget()

    def _create_startup_loading_overlay(self):
        overlay_bg = mix_color(self.config.theme_color, self.overlay_mix_base, self.overlay_mix_ratio)
        self.startup_loading_overlay = tk.Frame(self.root, bg=overlay_bg)
        self.startup_loading_box = tk.Frame(self.startup_loading_overlay, bg=self.card_color, padx=26, pady=20)
        self.startup_loading_box.place(relx=0.5, rely=0.5, anchor="center")
        self.startup_loading_icon_var = tk.StringVar(value="(^_^)")
        self.startup_loading_text_var = tk.StringVar(value="Initializing")
        self.startup_loading_icon_label = tk.Label(
            self.startup_loading_box,
            textvariable=self.startup_loading_icon_var,
            bg=self.card_color,
            fg=self.config.theme_color,
            font=(self.en_font_family, 17, "bold"),
        )
        self.startup_loading_icon_label.pack(anchor="center", pady=(0, 8))
        self.startup_loading_text_label = tk.Label(
            self.startup_loading_box,
            textvariable=self.startup_loading_text_var,
            bg=self.card_color,
            fg=self.text_secondary,
            font=(self.cn_font_family, 11),
        )
        self.startup_loading_text_label.pack(anchor="center", pady=(0, 10))
        self.startup_loading_tip_var = tk.StringVar(value="")
        self.startup_loading_tip_label = tk.Label(
            self.startup_loading_overlay,
            textvariable=self.startup_loading_tip_var,
            bg=overlay_bg,
            fg=self.text_secondary,
            font=(self.cn_font_family, 10),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.startup_loading_tip_label.place(relx=0.02, rely=0.98, anchor="sw")
        self.startup_loading_bar = ttk.Progressbar(
            self.startup_loading_box,
            orient="horizontal",
            mode="indeterminate",
            length=220,
        )
        self.startup_loading_bar.pack(anchor="center")
        self.startup_loading_overlay.place_forget()

    def _set_startup_loading_message(self, message):
        self.startup_loading_base_message = (message or "").strip() or "Initializing"

    def _show_startup_loading(self, message):
        if not hasattr(self, "startup_loading_overlay"):
            return
        self._set_startup_loading_message(message)
        self._start_tip_typewriter("startup", self._pick_loading_tip())
        self.startup_loading_running = True
        self.startup_loading_tick = 0
        if self.startup_loading_job is not None:
            self.root.after_cancel(self.startup_loading_job)
            self.startup_loading_job = None
        self.startup_loading_bar.start(15)
        self.startup_loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.startup_loading_overlay.lift()
        self._animate_startup_loading()

    def _animate_startup_loading(self):
        if not self.startup_loading_running:
            return
        frames = ["(o_o)", "(o_O)", "(O_o)", "(o_o)"]
        dots = "." * (self.startup_loading_tick % 4)
        self.startup_loading_icon_var.set(frames[self.startup_loading_tick % len(frames)])
        self.startup_loading_text_var.set(f"{self.startup_loading_base_message}{dots}")
        self.startup_loading_tick += 1
        self.startup_loading_job = self.root.after(220, self._animate_startup_loading)

    def _hide_startup_loading(self):
        self.startup_loading_running = False
        self._stop_tip_typewriter("startup")
        if self.startup_loading_job is not None:
            self.root.after_cancel(self.startup_loading_job)
            self.startup_loading_job = None
        if hasattr(self, "startup_loading_bar"):
            self.startup_loading_bar.stop()
        if hasattr(self, "startup_loading_overlay"):
            self.startup_loading_overlay.place_forget()

    def _set_study_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget_name in (
            "study_back_button",
            "study_count_spinbox",
            "study_difficulty_combo",
            "study_generate_button",
            "study_submit_button",
            "study_history_button",
            "quick_lookup_entry",
            "quick_lookup_button",
        ):
            if hasattr(self, widget_name):
                getattr(self, widget_name).configure(state=state)

    def _show_study_loading(self, message):
        if not hasattr(self, "study_loading_overlay"):
            return
        self.study_loading_base_message = (message or "").strip() or "铃兰正在忙碌中"
        self._start_tip_typewriter("study", self._pick_loading_tip())
        self.study_loading_running = True
        self.study_loading_tick = 0
        if self.study_loading_job is not None:
            self.root.after_cancel(self.study_loading_job)
            self.study_loading_job = None
        self.study_loading_bar.start(15)
        self.study_loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.study_loading_overlay.lift()
        self._animate_study_loading()

    def _animate_study_loading(self):
        if not self.study_loading_running:
            return
        frames = ["(o_o)", "(o_O)", "(O_o)", "(o_o)"]
        dots = "." * (self.study_loading_tick % 4)
        self.study_loading_icon_var.set(frames[self.study_loading_tick % len(frames)])
        self.study_loading_text_var.set(f"{self.study_loading_base_message}{dots}")
        self.study_loading_tick += 1
        self.study_loading_job = self.root.after(220, self._animate_study_loading)

    def _hide_study_loading(self):
        self.study_loading_running = False
        self._stop_tip_typewriter("study")
        if self.study_loading_job is not None:
            self.root.after_cancel(self.study_loading_job)
            self.study_loading_job = None
        if hasattr(self, "study_loading_bar"):
            self.study_loading_bar.stop()
        if hasattr(self, "study_loading_overlay"):
            self.study_loading_overlay.place_forget()

    def _apply_theme(self, color):
        btn_bg = mix_color(color, self.button_mix_base, self.button_mix_ratio)
        btn_active = mix_color(color, self.button_mix_base, self.button_active_ratio)
        self.style.configure(
            "TButton",
            font=(self.cn_font_family, 10),
            borderwidth=0,
            relief="flat",
            foreground="#ffffff",
            background=btn_bg,
        )
        self.style.map("TButton", background=[("active", btn_active)], foreground=[("active", "#ffffff")])
        self.root.configure(bg=self.bg_color)
        self.container.configure(bg=self.bg_color)
        self.icons_panel.configure(bg=self.bg_color)
        self.icons_row.configure(bg=self.bg_color)
        self.separator_label.configure(bg=self.bg_color)
        self.search_panel.configure(bg=self.card_color)
        if hasattr(self, "theme_color_text"):
            self.theme_color_text.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "mode_text"):
            self.mode_text.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "highlight_toggle_check"):
            self.highlight_toggle_check.configure(bg=self.card_color, fg=self.text_secondary, selectcolor=self.card_color, activebackground=self.card_color, activeforeground=self.text_secondary)
        if hasattr(self, "highlight_color_text"):
            self.highlight_color_text.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "highlight_color_block"):
            self.highlight_color_block.configure(bg=self.config.learning_highlight_color)
        if hasattr(self, "add_status_label"):
            self.add_status_label.configure(bg=self.bg_color, fg=self.text_secondary)
        if hasattr(self, "add_page"):
            self.add_page.configure(bg=self.bg_color)
        if hasattr(self, "add_page_panels"):
            for panel in self.add_page_panels:
                panel.configure(bg=self.card_color)
        if hasattr(self, "add_page_tags"):
            for tag in self.add_page_tags:
                tag_bg = self.bg_color if tag is self.add_page_title else self.card_color
                ratio = self.list_tag_fill_ratio if tag in (self.learning_tag, self.finished_tag) else self.tag_fill_ratio
                tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, ratio), outline=color, bg=tag_bg)
        if hasattr(self, "lookup_page"):
            self.lookup_page.configure(bg=self.bg_color)
        if hasattr(self, "lookup_page_panels"):
            for panel in self.lookup_page_panels:
                panel.configure(bg=self.card_color)
                for child in panel.winfo_children():
                    try:
                        if child.cget("bg") == self.card_color:
                            child.configure(bg=self.card_color)
                    except Exception:
                        pass
        if hasattr(self, "lookup_page_tags"):
            for tag in self.lookup_page_tags:
                tag_bg = self.bg_color if tag is self.lookup_title else self.card_color
                tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, self.tag_fill_ratio), outline=color, bg=tag_bg)
        if hasattr(self, "lookup_stats_label"):
            self.lookup_stats_label.configure(bg=self.bg_color, fg=color)
        if hasattr(self, "lookup_result_text"):
            self.lookup_result_text.configure(
                bg=mix_color(color, self.surface_mix_base, self.result_mix_ratio),
                fg=self.text_color,
                insertbackground=self.text_color,
            )
        if hasattr(self, "lookup_history_listbox"):
            self.lookup_history_listbox.configure(
                bg=mix_color(color, self.surface_mix_base, self.list_mix_ratio),
                fg=self.text_color,
                selectbackground=color,
                selectforeground="#ffffff",
            )
        if hasattr(self, "settings_page"):
            self.settings_page.configure(bg=self.bg_color)
        if hasattr(self, "settings_scroll_container"):
            self.settings_scroll_container.configure(bg=self.bg_color)
        if hasattr(self, "settings_scroll_canvas"):
            self.settings_scroll_canvas.configure(bg=self.bg_color)
        if hasattr(self, "settings_content"):
            self.settings_content.configure(bg=self.bg_color)
        if hasattr(self, "settings_page_panels"):
            for panel in self.settings_page_panels:
                panel.configure(bg=self.card_color)
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.configure(bg=self.bg_color, fg=self.text_secondary)
        for widget_name in (
            "settings_cn_font_label",
            "settings_en_font_label",
            "settings_size_label",
            "update_status_label",
        ):
            if hasattr(self, widget_name):
                getattr(self, widget_name).configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "settings_page_tags"):
            for tag in self.settings_page_tags:
                tag_bg = self.bg_color if tag is self.settings_title else self.card_color
                tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, self.tag_fill_ratio), outline=color, bg=tag_bg)
        if hasattr(self, "study_page"):
            self.study_page.configure(bg=self.bg_color)
        if hasattr(self, "study_page_panels"):
            for panel in self.study_page_panels:
                panel.configure(bg=self.card_color)
        if hasattr(self, "study_status_label"):
            self.study_status_label.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "study_count_label"):
            self.study_count_label.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "answer_panel"):
            self.answer_panel.configure(bg=self.card_color)
        if hasattr(self, "answer_canvas"):
            self.answer_canvas.configure(bg=self.card_color)
        if hasattr(self, "answer_scroll_container"):
            self.answer_scroll_container.configure(bg=self.card_color)
        if hasattr(self, "story_text_container"):
            self.story_text_container.configure(bg=self.card_color)
        if hasattr(self, "study_page_tags"):
            for tag in self.study_page_tags:
                tag_bg = self.bg_color if tag is self.study_title else self.card_color
                ratio = self.tag_fill_ratio if tag is not self.study_answer_tag else self.list_tag_fill_ratio
                tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, ratio), outline=color, bg=tag_bg)
        if hasattr(self, "competition_page"):
            self.competition_page.configure(bg=self.bg_color)
        if hasattr(self, "competition_page_panels"):
            for panel in self.competition_page_panels:
                try:
                    panel.configure(bg=self.card_color)
                except Exception:
                    pass
        if hasattr(self, "competition_today_label"):
            self.competition_today_label.configure(bg=self.bg_color, fg=color)
        if hasattr(self, "competition_review_label"):
            self.competition_review_label.configure(bg=self.bg_color, fg=color)
        if hasattr(self, "competition_page_tags"):
            for tag in self.competition_page_tags:
                tag_bg = self.bg_color if tag is self.competition_title else self.card_color
                tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, self.tag_fill_ratio), outline=color, bg=tag_bg)
        if hasattr(self, "competition_count_label"):
            self.competition_count_label.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "competition_start_label"):
            self.competition_start_label.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "competition_range_label"):
            self.competition_range_label.configure(bg=self.card_color, fg=self.text_color)
        if hasattr(self, "competition_hint_label"):
            self.competition_hint_label.configure(bg=self.card_color, fg=self.text_secondary)
        if hasattr(self, "competition_stopwatch_label"):
            self.competition_stopwatch_label.configure(bg=self.card_color, fg=color)
        if hasattr(self, "competition_result_frame"):
            self.competition_result_frame.configure(bg=self.card_color)
            for value_label in self.competition_result_labels.values():
                value_label.configure(bg=self.card_color, fg=self.text_color)
            for child in self.competition_result_frame.winfo_children():
                child.configure(bg=self.card_color)
                for sub in child.winfo_children():
                    try:
                        current_fg = sub.cget("fg")
                    except Exception:
                        current_fg = ""
                    sub.configure(bg=self.card_color)
                    if current_fg == self.text_color:
                        sub.configure(fg=self.text_color)
        if hasattr(self, "competition_status_label"):
            self.competition_status_label.configure(bg=self.bg_color, fg=self.text_secondary)
        if hasattr(self, "competition_page_checkbuttons"):
            for cb in self.competition_page_checkbuttons:
                try:
                    cb.configure(bg=self.card_color, fg=self.text_secondary,
                                 selectcolor=self.card_color, activebackground=self.card_color,
                                 activeforeground=self.text_secondary)
                except Exception:
                    pass
        if hasattr(self, "transition_overlay"):
            overlay_bg = mix_color(color, self.overlay_mix_base, self.overlay_mix_ratio)
            self.transition_overlay.configure(bg=overlay_bg)
            self.transition_label.configure(bg=overlay_bg, fg=color)
            if hasattr(self, "transition_tip_label"):
                self.transition_tip_label.configure(bg=overlay_bg, fg=self.text_secondary)
        if hasattr(self, "learning_listbox"):
            self.learning_listbox.configure(bg=mix_color(color, self.surface_mix_base, self.list_mix_ratio), fg=self.text_color, selectbackground=color, selectforeground="#ffffff")
        if hasattr(self, "finished_listbox"):
            self.finished_listbox.configure(bg=mix_color(color, self.surface_mix_base, self.list_mix_ratio), fg=self.text_color, selectbackground=color, selectforeground="#ffffff")
        if hasattr(self, "color_block"):
            self.color_block.configure(bg=color)
        if hasattr(self, "quick_lookup_output_text"):
            self.quick_lookup_output_text.configure(
                bg=mix_color(color, self.surface_mix_base, self.result_mix_ratio),
                fg=self.text_color,
                insertbackground=self.text_color,
            )
        if hasattr(self, "study_story_text"):
            self.study_story_text.configure(bg=self.card_color, fg=self.text_color, insertbackground=self.text_color)
        if hasattr(self, "story_prompt_text"):
            self.story_prompt_text.configure(bg=mix_color(color, self.surface_mix_base, self.prompt_mix_ratio), fg=self.text_color, insertbackground=self.text_color)
        if hasattr(self, "study_loading_overlay"):
            overlay_bg = mix_color(color, self.overlay_mix_base, self.overlay_mix_ratio)
            self.study_loading_overlay.configure(bg=overlay_bg)
            self.study_loading_box.configure(bg=self.card_color)
            self.study_loading_icon_label.configure(bg=self.card_color, fg=color)
            self.study_loading_text_label.configure(bg=self.card_color, fg=self.text_secondary)
            if hasattr(self, "study_loading_tip_label"):
                self.study_loading_tip_label.configure(bg=overlay_bg, fg=self.text_secondary)
        if hasattr(self, "startup_loading_overlay"):
            overlay_bg = mix_color(color, self.overlay_mix_base, self.overlay_mix_ratio)
            self.startup_loading_overlay.configure(bg=overlay_bg)
            self.startup_loading_box.configure(bg=self.card_color)
            self.startup_loading_icon_label.configure(bg=self.card_color, fg=color)
            self.startup_loading_text_label.configure(bg=self.card_color, fg=self.text_secondary)
            if hasattr(self, "startup_loading_tip_label"):
                self.startup_loading_tip_label.configure(bg=overlay_bg, fg=self.text_secondary)
        self.theme_var.set(f"主题色：{color}")
        self.result_text.configure(bg=mix_color(color, self.surface_mix_base, self.result_mix_ratio), fg=self.text_color, insertbackground=self.text_color)
        self.title_tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, self.title_fill_ratio), outline=color, bg=self.bg_color)
        self.search_tag.apply_theme(fg=color, fill=mix_color(color, self.tag_mix_base, self.search_fill_ratio), outline=color, bg=self.card_color)
        for tile in self.icon_tiles:
            tile.apply_theme(bg=self.bg_color, card_bg=self.card_color, border_color=color)
        for label in self.corner_labels:
            label.configure(bg=self.bg_color)
        self._apply_font_size()

    def _choose_theme_color(self):
        selected = colorchooser.askcolor(title="选择主题色", initialcolor=self.config.theme_color)
        if not selected or not selected[1]:
            return
        self._set_theme_color(selected[1])

    def _set_theme_color(self, color):
        self.config.theme_color = color
        self.config.save()
        self._apply_theme(color)

    def _apply_learning_word_highlight_settings(self):
        if hasattr(self, "learning_highlight_color_var"):
            self.learning_highlight_color_var.set(self.config.learning_highlight_color)
        if hasattr(self, "highlight_learning_words_var"):
            self.highlight_learning_words_var.set(self.config.highlight_learning_words)
        if hasattr(self, "highlight_color_block"):
            self.highlight_color_block.configure(bg=self.config.learning_highlight_color)
        if hasattr(self, "study_story_text"):
            self._configure_story_markdown_tags()
            self._highlight_learning_words_in_story()

    def _toggle_learning_word_highlight(self):
        self.config.highlight_learning_words = bool(self.highlight_learning_words_var.get())
        self.config.save()
        self._apply_learning_word_highlight_settings()
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(
                "Learning-word highlight enabled" if self.config.highlight_learning_words else "Learning-word highlight disabled"
            )

    def _choose_learning_highlight_color(self):
        selected = colorchooser.askcolor(
            title="Select learning-word highlight color",
            initialcolor=self.config.learning_highlight_color,
        )
        if not selected or not selected[1]:
            return
        self._set_learning_highlight_color(selected[1])

    def _set_learning_highlight_color(self, color):
        if not isinstance(color, str) or not re.match(r"^#[0-9a-fA-F]{6}$", color):
            return
        self.config.learning_highlight_color = color
        self.config.save()
        self._apply_learning_word_highlight_settings()
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(f"Learning highlight color set to {color}")

    def _apply_font_size(self):
        size_map = {"normal": 10, "large": 12, "xlarge": 14}
        base_size = size_map.get(self.config.font_size, 10)
        entry_size = base_size + 1
        text_size = base_size + 1
        self.style.configure("TButton", font=(self.cn_font_family, base_size))
        if hasattr(self, "search_entry"):
            self.search_entry.configure(font=(self.en_font_family, entry_size))
        if hasattr(self, "result_text"):
            self.result_text.configure(font=(self.en_font_family, text_size))
        if hasattr(self, "lookup_entry"):
            self.lookup_entry.configure(font=(self.en_font_family, text_size + 2))
        if hasattr(self, "lookup_stats_label"):
            self.lookup_stats_label.configure(font=(self.cn_font_family, base_size + 4, "bold"))
        if hasattr(self, "lookup_result_text"):
            self.lookup_result_text.configure(font=(self.en_font_family, text_size + 2))
        if hasattr(self, "lookup_history_listbox"):
            self.lookup_history_listbox.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "add_word_entry"):
            self.add_word_entry.configure(font=(self.en_font_family, entry_size))
        if hasattr(self, "import_entry"):
            self.import_entry.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "learning_listbox"):
            self.learning_listbox.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "finished_listbox"):
            self.finished_listbox.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "theme_color_text"):
            self.theme_color_text.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "mode_text"):
            self.mode_text.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "add_status_label"):
            self.add_status_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "update_status_label"):
            self.update_status_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "transition_label"):
            self.transition_label.configure(font=(self.cn_font_family, base_size + 3, "bold"))
        if hasattr(self, "transition_tip_label"):
            self.transition_tip_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "api_key_entry"):
            self.api_key_entry.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "study_count_spinbox"):
            self.study_count_spinbox.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "study_difficulty_combo"):
            self.study_difficulty_combo.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "study_story_text"):
            self.study_story_text.configure(font=(self.en_font_family, text_size))
            self._configure_story_markdown_tags()
        if hasattr(self, "story_prompt_text"):
            self.story_prompt_text.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "study_status_label"):
            self.study_status_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "quick_lookup_output_text"):
            self.quick_lookup_output_text.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "quick_lookup_entry"):
            self.quick_lookup_entry.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "highlight_toggle_check"):
            self.highlight_toggle_check.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "highlight_color_text"):
            self.highlight_color_text.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "cn_font_combo"):
            self.cn_font_combo.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "en_font_combo"):
            self.en_font_combo.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "font_size_combo"):
            self.font_size_combo.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "study_loading_icon_label"):
            self.study_loading_icon_label.configure(font=(self.en_font_family, base_size + 7, "bold"))
        if hasattr(self, "study_loading_text_label"):
            self.study_loading_text_label.configure(font=(self.cn_font_family, base_size + 1))
        if hasattr(self, "study_loading_tip_label"):
            self.study_loading_tip_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "startup_loading_icon_label"):
            self.startup_loading_icon_label.configure(font=(self.en_font_family, base_size + 7, "bold"))
        if hasattr(self, "startup_loading_text_label"):
            self.startup_loading_text_label.configure(font=(self.cn_font_family, base_size + 1))
        if hasattr(self, "startup_loading_tip_label"):
            self.startup_loading_tip_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "competition_count_label"):
            self.competition_count_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "competition_start_label"):
            self.competition_start_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "competition_count_combo"):
            self.competition_count_combo.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "competition_start_spinbox"):
            self.competition_start_spinbox.configure(font=(self.en_font_family, base_size))
        if hasattr(self, "competition_range_label"):
            self.competition_range_label.configure(font=(self.cn_font_family, base_size, "bold"))
        if hasattr(self, "competition_hint_label"):
            self.competition_hint_label.configure(font=(self.cn_font_family, 10))
        if hasattr(self, "competition_stopwatch_label"):
            self.competition_stopwatch_label.configure(font=(self.en_font_family, base_size + 24, "bold"))
        if hasattr(self, "competition_status_label"):
            self.competition_status_label.configure(font=(self.cn_font_family, base_size))
        if hasattr(self, "competition_today_label"):
            self.competition_today_label.configure(font=(self.cn_font_family, 18, "bold"))
        if hasattr(self, "competition_review_label"):
            self.competition_review_label.configure(font=(self.cn_font_family, 16, "bold"))
        if hasattr(self, "competition_filter_check"):
            self.competition_filter_check.configure(font=(self.cn_font_family, base_size))
        self._apply_font_family_to_tags()

    def _apply_font_family_to_tags(self):
        if hasattr(self, "title_tag"):
            self.title_tag.set_font((self.cn_font_family, 24, "bold"))
        if hasattr(self, "search_tag"):
            self.search_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "lookup_title"):
            self.lookup_title.set_font((self.cn_font_family, 18, "bold"))
        if hasattr(self, "lookup_search_tag"):
            self.lookup_search_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "lookup_result_tag"):
            self.lookup_result_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "lookup_history_tag"):
            self.lookup_history_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "add_page_title"):
            self.add_page_title.set_font((self.cn_font_family, 18, "bold"))
        if hasattr(self, "learning_tag"):
            self.learning_tag.set_font((self.cn_font_family, 11, "bold"))
        if hasattr(self, "finished_tag"):
            self.finished_tag.set_font((self.cn_font_family, 11, "bold"))
        if hasattr(self, "settings_title"):
            self.settings_title.set_font((self.cn_font_family, 18, "bold"))
        if hasattr(self, "settings_theme_tag"):
            self.settings_theme_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_font_tag"):
            self.settings_font_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_api_tag"):
            self.settings_api_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_account_tag"):
            self.settings_account_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_prompt_tag"):
            self.settings_prompt_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_update_tag"):
            self.settings_update_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "settings_highlight_tag"):
            self.settings_highlight_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "study_title"):
            self.study_title.set_font((self.cn_font_family, 18, "bold"))
        if hasattr(self, "study_control_tag"):
            self.study_control_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "study_story_tag"):
            self.study_story_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "study_answer_tag"):
            self.study_answer_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "competition_title"):
            self.competition_title.set_font((self.cn_font_family, 18, "bold"))
        if hasattr(self, "competition_control_tag"):
            self.competition_control_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "competition_history_tag"):
            self.competition_history_tag.set_font((self.cn_font_family, 12, "bold"))
        if hasattr(self, "competition_current_tag"):
            self.competition_current_tag.set_font((self.cn_font_family, 12, "bold"))

    def _on_font_size_change(self, _event=None):
        value = self.font_size_var.get()
        if value not in ("normal", "large", "xlarge"):
            return
        self.config.font_size = value
        self.config.save()
        self._apply_font_size()
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(f"字体大小已切换为：{value}")

    def _on_cn_font_change(self, _event=None):
        value = self.cn_font_var.get().strip()
        if not value:
            return
        self.cn_font_family = self._resolve_font_family(value, CN_FONT_CANDIDATES)
        self.cn_font_var.set(self.cn_font_family)
        self.config.cn_font = self.cn_font_family
        self.config.save()
        self._apply_theme(self.config.theme_color)
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(f"中文字体已切换为：{self.cn_font_family}")

    def _on_en_font_change(self, _event=None):
        value = self.en_font_var.get().strip()
        if not value:
            return
        self.en_font_family = self._resolve_font_family(value, EN_FONT_CANDIDATES)
        self.en_font_var.set(self.en_font_family)
        self.config.en_font = self.en_font_family
        self.config.save()
        self._apply_font_size()
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set(f"英文字体已切换为：{self.en_font_family}")

    def _save_api_key(self):
        self._save_env_vars()

    def _save_env_vars(self):
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip().rstrip("/")
        if not base_url:
            base_url = DEFAULT_BASE_URL
        if not base_url.endswith("/v1"):
            base_url = base_url + "/v1"
        env_path = ENV_PATH
        lines = [f"API_KEY={api_key}\n", f"BASE_URL={base_url}\n"]
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        self._load_env_settings()
        self._refresh_env_labels()
        if self.dotenv_enabled:
            self.settings_status_var.set("已写入 .env 并重新加载")
        else:
            self.settings_status_var.set("已写入 .env（建议安装 python-dotenv: pip install python-dotenv）")

    def _reload_env_vars(self):
        self._load_env_settings()
        self._refresh_env_labels()
        if not self.api_key:
            if self.dotenv_enabled:
                self.settings_status_var.set("未读取到 API_KEY，请在 .env 中配置")
            else:
                self.settings_status_var.set("未读取到 API_KEY（建议安装 python-dotenv: pip install python-dotenv）")
            return
        if self.dotenv_enabled:
            self.settings_status_var.set("已从 .env 重新加载 API_KEY 和 BASE_URL")
        else:
            self.settings_status_var.set("已从 .env 读取 API_KEY 和 BASE_URL")

    def _check_for_updates(self):
        if self.update_check_running:
            return
        if not self.update_service.github_repo:
            self.update_status_var.set("尚未配置 GitHub 仓库地址")
            return
        self.update_check_running = True
        self.latest_release_info = {}
        self.update_status_var.set("正在检查 GitHub 最新版本...")
        if hasattr(self, "check_update_button"):
            self.check_update_button.configure(state="disabled")
        if hasattr(self, "download_update_button"):
            self.download_update_button.configure(state="disabled")
        if hasattr(self, "release_page_button"):
            self.release_page_button.configure(state="disabled")

        worker = threading.Thread(target=self._check_for_updates_worker, daemon=True)
        worker.start()

    def _check_for_updates_worker(self):
        try:
            release_info = self.update_service.fetch_latest_release()
            self.root.after(0, lambda info=release_info: self._on_update_check_success(info))
        except Exception as exc:
            message = str(exc) or "检查更新失败"
            self.root.after(0, lambda msg=message: self._on_update_check_failed(msg))

    def _on_update_check_success(self, release_info):
        self.update_check_running = False
        self.latest_release_info = release_info or {}
        latest_tag = self.latest_release_info.get("tag_name") or (
            "v%s" % (self.latest_release_info.get("version") or "")
        )
        if self.latest_release_info.get("has_update"):
            self.update_status_var.set(f"发现新版本：{latest_tag}，当前版本：v{APP_VERSION}")
            if hasattr(self, "download_update_button"):
                self.download_update_button.configure(
                    state="normal" if self.latest_release_info.get("asset_url") else "disabled"
                )
            if hasattr(self, "release_page_button"):
                self.release_page_button.configure(state="normal")
            if hasattr(self, "settings_status_var"):
                self.settings_status_var.set("发现新版本，可以下载新版或打开发布页查看说明")
        else:
            self.update_status_var.set(f"当前已是最新版本：v{APP_VERSION}")
            if hasattr(self, "release_page_button"):
                self.release_page_button.configure(state="normal")
            if hasattr(self, "settings_status_var"):
                self.settings_status_var.set("当前已是最新版本")
        if hasattr(self, "check_update_button"):
            self.check_update_button.configure(state="normal")

    def _on_update_check_failed(self, message):
        self.update_check_running = False
        self.update_status_var.set(f"检查更新失败：{message}")
        if hasattr(self, "check_update_button"):
            self.check_update_button.configure(state="normal")
        if hasattr(self, "settings_status_var"):
            self.settings_status_var.set("检查更新失败，请确认网络连接后重试")

    def _open_update_download(self):
        url = (self.latest_release_info or {}).get("asset_url") or ""
        if not url:
            self._open_release_page()
            return
        webbrowser.open(url)

    def _open_release_page(self):
        url = (self.latest_release_info or {}).get("release_url") or self.update_service.latest_release_url()
        if not url:
            if hasattr(self, "settings_status_var"):
                self.settings_status_var.set("尚未配置 GitHub 仓库地址")
            return
        webbrowser.open(url)

    def _current_settings_payload(self):
        return {
            "theme_color": self.config.theme_color,
            "theme_mode": self.config.theme_mode,
            "font_size": self.config.font_size,
            "cn_font": self.config.cn_font,
            "en_font": self.config.en_font,
            "story_prompt": self.config.story_prompt,
            "study_word_count": self.config.study_word_count,
            "study_difficulty": self.config.study_difficulty,
            "highlight_learning_words": self.config.highlight_learning_words,
            "learning_highlight_color": self.config.learning_highlight_color,
        }

    def _apply_imported_settings(self, settings):
        if not isinstance(settings, dict):
            return
        color = settings.get("theme_color")
        if isinstance(color, str) and color.strip():
            self.config.theme_color = color.strip()
        mode = settings.get("theme_mode")
        if mode in ("day", "night"):
            self.config.theme_mode = mode
        size = settings.get("font_size")
        if size in ("normal", "large", "xlarge"):
            self.config.font_size = size
        cn_font = settings.get("cn_font")
        if isinstance(cn_font, str):
            self.config.cn_font = cn_font
        en_font = settings.get("en_font")
        if isinstance(en_font, str):
            self.config.en_font = en_font
        prompt = settings.get("story_prompt")
        if isinstance(prompt, str) and prompt.strip():
            self.config.story_prompt = prompt
            self.story_prompt_var.set(prompt)
        count = settings.get("study_word_count")
        if isinstance(count, int):
            self.config.study_word_count = max(5, min(20, count))
        difficulty = settings.get("study_difficulty")
        if difficulty in ("easy", "normal", "hard"):
            self.config.study_difficulty = difficulty
        highlight_learning_words = settings.get("highlight_learning_words")
        if isinstance(highlight_learning_words, bool):
            self.config.highlight_learning_words = highlight_learning_words
        learning_highlight_color = settings.get("learning_highlight_color")
        if isinstance(learning_highlight_color, str) and re.match(r"^#[0-9a-fA-F]{6}$", learning_highlight_color):
            self.config.learning_highlight_color = learning_highlight_color

        self.config.save()
        self.theme_var.set(f"????{self.config.theme_color}")
        self.font_size_var.set(self.config.font_size)
        self.study_word_count_var.set(self.config.study_word_count)
        self.study_difficulty_var.set(self.config.study_difficulty)
        self.highlight_learning_words_var.set(self.config.highlight_learning_words)
        self.learning_highlight_color_var.set(self.config.learning_highlight_color)
        self.cn_font_family = self._resolve_font_family(self.config.cn_font, CN_FONT_CANDIDATES)
        self.en_font_family = self._resolve_font_family(self.config.en_font, EN_FONT_CANDIDATES)
        self.cn_font_var.set(self.cn_font_family)
        self.en_font_var.set(self.en_font_family)
        self._apply_theme_mode()
        self._apply_theme(self.config.theme_color)
        self._apply_font_size()
        self._apply_learning_word_highlight_settings()
        self._sync_story_prompt_text_from_config()

    def _apply_imported_env(self, env_data):
        if not isinstance(env_data, dict):
            return
        api_key = (env_data.get("API_KEY") or "").strip()
        base_url = (env_data.get("BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
        if not base_url:
            base_url = DEFAULT_BASE_URL
        if not base_url.endswith("/v1"):
            base_url = base_url + "/v1"
        lines = [f"API_KEY={api_key}\n", f"BASE_URL={base_url}\n"]
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        self._load_env_settings()
        self._refresh_env_labels()

    def _export_account_data(self):
        path = filedialog.asksaveasfilename(
            title="??????",
            defaultextension=".slaccount",
            filetypes=[("Account Files", "*.slaccount"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile="??????.slaccount",
        )
        if not path:
            return
        try:
            self._load_env_settings()
            self._refresh_env_labels()
            result = self.account_service.export_account(
                path,
                settings_data=self._current_settings_payload(),
                env_data={"API_KEY": self.api_key, "BASE_URL": self.base_url},
            )
            self.settings_status_var.set(
                f"?????????{result['lists_count']}????{result['progress_count']}????{result['history_count']}?"
            )
        except Exception as e:
            self.settings_status_var.set(f"???????{e}")

    def _import_account_data(self):
        path = filedialog.askopenfilename(
            title="??????",
            filetypes=[("Account Files", "*.slaccount"), ("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            result = self.account_service.import_account(path)
            self._apply_imported_settings(result.get("settings") or {})
            self._apply_imported_env(result.get("env") or {})
            self._refresh_personal_lists()
            self.settings_status_var.set(
                f"?????????{result['lists_count']}????{result['progress_count']}????{result['history_count']}?"
            )
        except Exception as e:
            self.settings_status_var.set(f"???????{e}")

    def _save_story_prompt(self):
        text = self.story_prompt_text.get("1.0", tk.END).strip()
        if not text:
            self.settings_status_var.set("提示词不能为空")
            return
        self.config.story_prompt = text
        self.story_prompt_var.set(text)
        self.config.save()
        self.settings_status_var.set("提示词已保存")

    def _update_story_prompt(self):
        self._save_story_prompt()
        self._sync_story_prompt_text_from_config()
        self.settings_status_var.set("提示词已更新并重载")

    def _sync_story_prompt_text_from_config(self):
        if not hasattr(self, "story_prompt_text"):
            return
        current = self.story_prompt_text.get("1.0", tk.END).strip()
        target = (self.config.story_prompt or "").strip()
        if target.strip() == LEGACY_STORY_PROMPT.strip():
            target = DEFAULT_STORY_PROMPT
            self.config.story_prompt = target
            self.config.save()
        if not target:
            target = DEFAULT_STORY_PROMPT
            self.config.story_prompt = target
            self.config.save()
        if current != target:
            self.story_prompt_text.delete("1.0", tk.END)
            self.story_prompt_text.insert("1.0", target)
        self.story_prompt_var.set(target)

    def _get_story_prompt_for_generation(self):
        if hasattr(self, "story_prompt_text"):
            text = self.story_prompt_text.get("1.0", tk.END).strip()
            if text.strip() == LEGACY_STORY_PROMPT.strip():
                text = DEFAULT_STORY_PROMPT
            if text and text != self.config.story_prompt:
                self.config.story_prompt = text
                self.story_prompt_var.set(text)
                self.config.save()
                return text
        template = (self.config.story_prompt or "").strip()
        if template.strip() == LEGACY_STORY_PROMPT.strip():
            template = DEFAULT_STORY_PROMPT
            self.config.story_prompt = template
            self.story_prompt_var.set(template)
            self.config.save()
        if not template:
            template = DEFAULT_STORY_PROMPT
            self.config.story_prompt = template
            self.story_prompt_var.set(template)
            self.config.save()
        return template

    def _save_study_word_count(self):
        try:
            value = int(self.study_word_count_var.get())
        except Exception:
            value = 10
        value = min(20, max(5, value))
        self.study_word_count_var.set(value)
        self.config.study_word_count = value
        self.config.save()

    def _save_study_difficulty(self):
        value = (self.study_difficulty_var.get() or "normal").strip().lower()
        if value not in ("easy", "normal", "hard"):
            value = "normal"
        self.study_difficulty_var.set(value)
        self.config.study_difficulty = value
        self.config.save()

    def _on_study_difficulty_change(self, _event=None):
        self._save_study_difficulty()

    def _build_story_difficulty_prompt(self):
        value = (self.study_difficulty_var.get() or "normal").strip().lower()
        hints = {
            "easy": "Reading Difficulty: easy. Target level: Chinese middle school entrance exam reading (??). Use short sentences, common vocabulary, and straightforward grammar.",
            "normal": "Reading Difficulty: normal. Target level: Chinese college entrance exam reading (??). Use moderate sentence variety and mid-frequency vocabulary.",
            "hard": "Reading Difficulty: hard. Target level: CET-6 reading (??). Use more advanced vocabulary, denser information, and varied complex sentence structures.",
        }
        return hints.get(value, hints["normal"])

    def _start_initialize(self):
        self.color_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.search_entry.configure(state="disabled")
        self._set_add_page_enabled(False)
        self._set_result_text("Dictionary is initializing. Please wait...")
        self._show_startup_loading("Preparing dictionary")
        worker = threading.Thread(target=self._initialize_dictionary_worker, daemon=True)
        worker.start()

    def _initialize_dictionary_worker(self):
        try:
            self.dictionary_service.initialize_if_empty()
            self.translation_preload_error = ""
            self.root.after(0, lambda: self._set_startup_loading_message("Preloading translator"))
            try:
                self.translation_service.preload()
            except Exception as preload_error:
                self.translation_preload_error = str(preload_error)
            self.root.after(0, self._finish_initialize)
        except Exception as e:
            self.root.after(0, lambda: self._fail_initialize(str(e)))

    def _finish_initialize(self):
        self._hide_startup_loading()
        self.color_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.search_entry.configure(state="normal")
        self.initialized = True
        self._set_add_page_enabled(True)
        self._refresh_personal_lists()
        self.search_entry.focus_set()
        if self.translation_preload_error:
            self._set_result_text("Ready. Translator warmup failed, first sentence lookup may be slower.")
        else:
            self._set_result_text("Ready. 输入会自动查词；按 Enter 会记录一次查询并清空输入框。")

    def _fail_initialize(self, message):
        self._hide_startup_loading()
        self.color_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.search_entry.configure(state="normal")
        self._set_add_page_enabled(True)
        self._set_result_text(f"Initialization failed: {message}")

    def _set_result_text(self, content):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", content)
        self.result_text.configure(state="disabled")

    def _on_quick_lookup_result_var_change(self, *_args):
        self._sync_quick_lookup_output()

    def _sync_quick_lookup_output(self):
        if not hasattr(self, "quick_lookup_output_text"):
            return
        content = self.quick_lookup_result_var.get()
        self.quick_lookup_output_text.configure(state="normal")
        self.quick_lookup_output_text.delete("1.0", tk.END)
        if content:
            self.quick_lookup_output_text.insert("1.0", content)
        self.quick_lookup_output_text.configure(state="disabled")

    def _set_quick_lookup_result(self, content):
        self.quick_lookup_result_var.set((content or "").strip())
        self._sync_quick_lookup_output()

    def _is_sentence_query(self, keyword):
        return len((keyword or "").split()) >= 2


    def _normalize_lookup_text(self, raw_text):
        text = re.sub(r"\s+", " ", (raw_text or "").strip())
        if not text:
            return ""
        return re.sub(r"^[^\w\u4e00-\u9fff]+|[^\w\u4e00-\u9fff]+$", "", text)

    def _lookup_meaning_brief(self, raw_text):
        keyword = self._normalize_lookup_text(raw_text)
        if not keyword:
            return ""
        if self._is_sentence_query(keyword):
            translated = self.translation_service.translate_sentence(keyword)
            translated = (translated or "").strip()
            return translated or "翻译结果为空"

        matches = self.dictionary_service.find_lookup_matches(keyword, limit=3)
        if not matches:
            return "未找到翻译"
        first = matches[0]
        core = self._word_core_translation(first.get("translation") or "")
        if (first.get("word") or "").lower() != keyword.lower():
            return f"相近：{first.get('word')}  {core}"
        return core

    def _find_exact_lookup_record(self, raw_text):
        keyword = self._normalize_lookup_text(raw_text)
        if not keyword or self._is_sentence_query(keyword):
            return None
        matches = self.dictionary_service.find_lookup_matches(keyword, limit=1)
        if not matches:
            return None
        record = matches[0]
        if (record.get("word") or "").lower() != keyword.lower():
            return None
        return record

    def _build_lookup_output(self, keyword):
        keyword = (keyword or "").strip()
        if not keyword:
            return self._pick_home_tip(), None
        if self._is_sentence_query(keyword):
            try:
                translated = self.translation_service.translate_sentence(keyword)
            except Exception as e:
                return (
                    "句子翻译失败。\n"
                    f"原因：{e}\n\n"
                    "可尝试：\n"
                    "1) pip install argostranslate\n"
                    "2) 检查网络后重试（首次会下载翻译模型）"
                ), None
            translated = (translated or "").strip()
            if not translated:
                return f"原句：{keyword}\n\n翻译结果为空", None
            return f"原句：{keyword}\n\n翻译：{translated}", None

        matches = self.dictionary_service.find_lookup_matches(keyword, limit=8)
        if not matches:
            return f"未找到：{keyword}", None

        normalized = keyword.lower()
        primary = matches[0]
        exact = (primary.get("word") or "").lower() == normalized
        lines = []
        if not exact:
            lines.append(f"未找到精确结果：{keyword}")
            lines.append("为你找到可能相近的单词：")
            lines.append("")
        lines.append(self._format_word_detail(primary))
        suggestions = [
            item for item in matches[1:]
            if (item.get("word") or "").lower() != (primary.get("word") or "").lower()
        ]
        if suggestions:
            lines.extend(["", "相近词："])
            for item in suggestions[:6]:
                word = item.get("word") or ""
                phonetic = item.get("phonetic") or ""
                core = self._word_core_translation(item.get("translation") or "")
                phonetic_part = f" [{phonetic}]" if phonetic else ""
                lines.append(f"- {word}{phonetic_part}：{core}")
        return "\n".join(lines), primary

    def _set_lookup_page_result_text(self, content):
        if not hasattr(self, "lookup_result_text"):
            return
        self.lookup_result_text.configure(state="normal")
        self.lookup_result_text.delete("1.0", tk.END)
        self.lookup_result_text.insert("1.0", content)
        self.lookup_result_text.configure(state="disabled")

    def _refresh_lookup_result(self, target):
        if not getattr(self, "initialized", False):
            return
        if target == "full":
            keyword = self.lookup_word_var.get().strip()
            if not keyword:
                self._set_lookup_page_result_text("")
                self.full_lookup_job = None
                return
            text, _record = self._build_lookup_output(keyword)
            self._set_lookup_page_result_text(text)
            self.full_lookup_job = None
            return
        keyword = self.search_word_var.get().strip()
        text, _record = self._build_lookup_output(keyword)
        self._set_result_text(text)
        self.home_lookup_job = None

    def _schedule_lookup_refresh(self, target):
        job_attr = "full_lookup_job" if target == "full" else "home_lookup_job"
        job = getattr(self, job_attr, None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        setattr(self, job_attr, self.root.after(220, lambda: self._refresh_lookup_result(target)))

    def _on_search_word_var_change(self, *_args):
        self._schedule_lookup_refresh("home")

    def _on_lookup_word_var_change(self, *_args):
        self._schedule_lookup_refresh("full")

    def _record_lookup_submit(self, keyword):
        keyword = (keyword or "").strip()
        if not keyword:
            return
        today = self._today_lookup_key()
        stats = self.lookup_stats
        stats["total_count"] = int(stats.get("total_count", 0) or 0) + 1
        daily_counts = stats.setdefault("daily_counts", {})
        daily_counts[today] = int(daily_counts.get(today, 0) or 0) + 1

        _text, record = self._build_lookup_output(keyword)
        if record:
            history = stats.setdefault("history", [])
            word = (record.get("word") or keyword).strip()
            history.insert(
                0,
                {
                    "query": keyword,
                    "word": word,
                    "phonetic": record.get("phonetic") or "",
                    "core_translation": self._word_core_translation(record.get("translation") or ""),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            seen = set()
            deduped = []
            for item in history:
                key = ((item.get("query") or "").lower(), (item.get("word") or "").lower())
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(item)
            stats["history"] = deduped[:80]

        self._save_lookup_stats()
        self._refresh_lookup_stats_view()

    def _clear_lookup_entry(self):
        self.lookup_word_var.set("")
        self._set_lookup_page_result_text("")
        return "break"

    def _on_lookup_enter(self, _event=None):
        keyword = self.lookup_word_var.get().strip()
        if keyword:
            self._record_lookup_submit(keyword)
        return self._clear_lookup_entry()

    def _on_search_enter(self, _event):
        keyword = self.search_word_var.get().strip()
        if keyword:
            self._record_lookup_submit(keyword)
        self.search_word_var.set("")
        self._set_result_text(self._pick_home_tip())
        return "break"

    def _search_word(self):
        self._refresh_lookup_result("home")

    def _search_lookup_page(self):
        self._refresh_lookup_result("full")

    def _active_lookup_target(self):
        if hasattr(self, "lookup_page") and self.lookup_page.winfo_ismapped():
            return "full", self.lookup_word_var.get().strip()
        return "home", self.search_word_var.get().strip()

    def _show_pronunciation_message(self, target, message):
        message = (message or "").strip()
        if not message:
            return
        if target == "full":
            if not hasattr(self, "lookup_result_text"):
                return
            current = self.lookup_result_text.get("1.0", tk.END).strip()
            content = f"{current}\n\n{message}" if current else message
            self._set_lookup_page_result_text(content)
            return
        self._set_result_text(message)

    def _on_pronunciation_done(self, target, ok, status):
        def update():
            if ok:
                return
            if status == "no_word":
                message = "请输入一个英文单词后再播放语音。"
            else:
                message = "语音播放失败，请稍后再试。"
            self._show_pronunciation_message(target, message)

        self.root.after(0, update)

    def _play_current_lookup_pronunciation(self, _event=None):
        if not getattr(self, "initialized", False):
            self._set_result_text("词库初始化中，请稍候")
            return "break"
        target, keyword = self._active_lookup_target()
        record = self._find_exact_lookup_record(keyword)
        if not record:
            self._show_pronunciation_message(target, "未找到精确匹配，无法播放语音。")
            return "break"
        word = record.get("word") or keyword
        self.pronunciation_service.play_word(
            word,
            record,
            on_done=lambda ok, status: self._on_pronunciation_done(target, ok, status),
        )
        return "break"

    def _open_lookup_history_item(self, _event=None):
        if not hasattr(self, "lookup_history_listbox"):
            return
        selection = self.lookup_history_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index < 0 or index >= len(self.lookup_history_items):
            return
        item = self.lookup_history_items[index]
        word = (item.get("word") or item.get("query") or "").strip()
        if word:
            self.lookup_word_var.set(word)

    def _set_add_page_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget_name in (
            "back_button",
            "add_word_entry",
            "add_word_button",
            "import_entry",
            "import_browse_button",
            "import_button",
            "export_button",
            "lookup_full_button",
            "lookup_back_button",
            "lookup_entry",
            "lookup_search_button",
            "lookup_play_button",
            "lookup_clear_button",
            "settings_back_button",
            "color_button",
            "day_mode_button",
            "night_mode_button",
            "cn_font_combo",
            "en_font_combo",
            "font_size_combo",
            "api_key_entry",
            "base_url_entry",
            "api_key_save_button",
            "env_reload_button",
            "account_import_button",
            "account_export_button",
            "check_update_button",
            "download_update_button",
            "release_page_button",
            "study_back_button",
            "study_count_spinbox",
            "study_generate_button",
            "study_submit_button",
            "study_history_button",
            "quick_lookup_entry",
            "quick_lookup_button",
            "story_prompt_text",
            "update_prompt_button",
            "story_prompt_save_button",
            "highlight_toggle_check",
            "highlight_color_button",
            "competition_back_button",
            "competition_count_combo",
            "competition_start_spinbox",
            "competition_export_button",
            "competition_invalid_button",
        ):
            if hasattr(self, widget_name):
                getattr(self, widget_name).configure(state=state)

    def _open_settings_page(self):
        if not self.initialized:
            self._set_result_text("词库初始化中，请稍候")
            return
        self._run_transition(self._show_settings_page)

    def _open_study_page(self):
        if not self.initialized:
            self._set_result_text("词库初始化中，请稍候")
            return
        self._run_transition(self._show_study_page)

    def _open_add_page(self):
        if not self.initialized:
            self._set_result_text("词库初始化中，请稍候")
            return
        self._run_transition(self._show_add_page)

    def _open_lookup_page(self):
        if not self.initialized:
            self._set_result_text("词库初始化中，请稍候")
            return
        self._run_transition(self._show_lookup_page)

    def _open_competition_page(self):
        if not self.initialized:
            self._set_result_text("词库初始化中，请稍候")
            return
        self._run_transition(self._show_competition_page)

    def _back_to_main(self):
        self._run_transition(self._show_main_page)

    def _show_add_page(self):
        self.container.pack_forget()
        if hasattr(self, "lookup_page"):
            self.lookup_page.pack_forget()
        if hasattr(self, "competition_page"):
            competition_actions.leave_competition_page(self)
            self.competition_page.pack_forget()
        self.add_page.pack(fill="both", expand=True)
        self._refresh_personal_lists()

    def _show_main_page(self):
        self.add_page.pack_forget()
        if hasattr(self, "settings_page"):
            self.settings_page.pack_forget()
        if hasattr(self, "lookup_page"):
            self.lookup_page.pack_forget()
        if hasattr(self, "study_page"):
            self.study_page.pack_forget()
        if hasattr(self, "competition_page"):
            competition_actions.leave_competition_page(self)
            self.competition_page.pack_forget()
        self.container.pack(fill="both", expand=True)

    def _show_settings_page(self):
        self.container.pack_forget()
        self.add_page.pack_forget()
        if hasattr(self, "lookup_page"):
            self.lookup_page.pack_forget()
        if hasattr(self, "study_page"):
            self.study_page.pack_forget()
        if hasattr(self, "competition_page"):
            competition_actions.leave_competition_page(self)
            self.competition_page.pack_forget()
        self._sync_story_prompt_text_from_config()
        self.settings_page.pack(fill="both", expand=True)
        if hasattr(self, "settings_scroll_canvas"):
            self.settings_scroll_canvas.update_idletasks()
            self.settings_scroll_canvas.configure(scrollregion=self.settings_scroll_canvas.bbox("all"))
            self.settings_scroll_canvas.yview_moveto(0)
        if not self.update_auto_checked:
            self.update_auto_checked = True
            self.root.after(400, self._check_for_updates)

    def _show_lookup_page(self):
        self.container.pack_forget()
        self.add_page.pack_forget()
        if hasattr(self, "settings_page"):
            self.settings_page.pack_forget()
        if hasattr(self, "study_page"):
            self.study_page.pack_forget()
        if hasattr(self, "competition_page"):
            competition_actions.leave_competition_page(self)
            self.competition_page.pack_forget()
        current = self.search_word_var.get().strip()
        if current and not self.lookup_word_var.get().strip():
            self.lookup_word_var.set(current)
        self._refresh_lookup_stats_view()
        self.lookup_page.pack(fill="both", expand=True)
        self.lookup_entry.focus_set()
        self._refresh_lookup_result("full")

    def _show_study_page(self):
        self.container.pack_forget()
        self.add_page.pack_forget()
        if hasattr(self, "lookup_page"):
            self.lookup_page.pack_forget()
        if hasattr(self, "settings_page"):
            self.settings_page.pack_forget()
        if hasattr(self, "competition_page"):
            competition_actions.leave_competition_page(self)
            self.competition_page.pack_forget()
        self.study_page.pack(fill="both", expand=True)
        self._hide_study_loading()
        self._set_study_controls_enabled(True)
        self._refresh_personal_lists()
        self._set_quick_lookup_result("")
        self.study_status_var.set("点击“生成故事”开始练习")

    def _show_competition_page(self):
        self.container.pack_forget()
        self.add_page.pack_forget()
        if hasattr(self, "lookup_page"):
            self.lookup_page.pack_forget()
        if hasattr(self, "settings_page"):
            self.settings_page.pack_forget()
        if hasattr(self, "study_page"):
            self.study_page.pack_forget()
        self.competition_page.pack(fill="both", expand=True)
        competition_actions.enter_competition_page(self)

    def _run_transition(self, on_finish):
        if self.transition_running:
            return
        self.transition_running = True
        self._start_tip_typewriter("transition", self._pick_loading_tip())
        self.transition_bar.configure(value=0)
        self.transition_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.transition_overlay.lift()
        steps = 10
        total_ms = random.randint(TRANSITION_MIN_MS, TRANSITION_MAX_MS)
        interval = max(1, round(total_ms / steps))
        try:
            self.root.attributes("-alpha", 0.9)
        except Exception:
            pass

        def step(index):
            value = int(index * 100 / steps)
            self.transition_bar.configure(value=value)
            try:
                self.root.attributes("-alpha", 0.9 + 0.1 * index / steps)
            except Exception:
                pass
            if index >= steps:
                on_finish()
                self.transition_overlay.place_forget()
                self._stop_tip_typewriter("transition")
                try:
                    self.root.attributes("-alpha", 1.0)
                except Exception:
                    pass
                self.transition_running = False
                return
            self.root.after(interval, lambda: step(index + 1))

        step(0)

    def _add_single_word(self, _event=None):
        return add_actions.add_single_word(self, _event)

    def _select_import_file(self):
        return add_actions.select_import_file(self)

    def _import_words(self):
        return add_actions.import_words(self)

    def _export_learning_words(self):
        return add_actions.export_learning_words(self)

    def _refresh_personal_lists(self):
        return add_actions.refresh_personal_lists(self)

    def _open_word_menu(self, event, list_name):
        return add_actions.open_word_menu(self, event, list_name)

    def _query_menu_word(self):
        return add_actions.query_menu_word(self)

    def _remove_menu_word(self):
        return add_actions.remove_menu_word(self)

    def _query_selected_word(self, list_name):
        return add_actions.query_selected_word(self, list_name)

    def _show_word_query(self, word):
        return add_actions.show_word_query(self, word)

    def _generate_study_story(self):
        return study_actions.generate_study_story(self)

    def _generate_story_worker(self, prompt, request_id):
        return study_actions.generate_story_worker(self, prompt, request_id)

    def _check_story_timeout(self, request_id):
        return study_actions.check_story_timeout(self, request_id)

    def _call_llm(self, prompt):
        return study_actions.call_llm(self, prompt)

    def _configure_story_markdown_tags(self):
        return study_actions.configure_story_markdown_tags(self)

    def _highlight_learning_words_in_story(self):
        return study_actions.highlight_learning_words_in_story(self)

    def _save_story_markdown(self, markdown_text):
        return study_actions.save_story_markdown(self, markdown_text)

    def _build_history_markdown(self, story_text, rows, correct_count, total_count, moved_words):
        return study_actions.build_history_markdown(self, story_text, rows, correct_count, total_count, moved_words)

    def _list_study_history_files(self):
        return study_actions.list_study_history_files(self)

    def _load_history_file_text(self, file_path):
        return study_actions.load_history_file_text(self, file_path)

    def _open_study_history(self):
        return study_actions.open_study_history(self)

    def _render_story_markdown(self, markdown_text):
        return study_actions.render_story_markdown(self, markdown_text)

    def _on_story_generated(self, request_id, story):
        return study_actions.on_story_generated(self, request_id, story)

    def _on_story_failed(self, request_id, message):
        return study_actions.on_story_failed(self, request_id, message)

    def _build_answer_inputs(self):
        return study_actions.build_answer_inputs(self)

    def _focus_answer_index(self, index):
        return study_actions.focus_answer_index(self, index)

    def _feedback_gap(self, message):
        return study_actions.feedback_gap(self, message)

    def _set_answer_feedback(self, index, message, color):
        return study_actions.set_answer_feedback(self, index, message, color)

    def _extract_story_order(self, story, default_items):
        return study_actions.extract_story_order(self, story, default_items)

    def _quick_lookup_word(self, _event=None):
        return study_actions.quick_lookup_word(self, _event)


    def _lookup_selected_story_text(self, _event=None):
        return study_actions.lookup_selected_story_text(self, _event)

    def _extract_json_block(self, text):
        return study_actions.extract_json_block(self, text)

    def _judge_answers_with_llm(self, story, items):
        return study_actions.judge_answers_with_llm(self, story, items)

    def _submit_review_worker(self, story, items, request_id):
        return study_actions.submit_review_worker(self, story, items, request_id)

    def _check_review_timeout(self, request_id):
        return study_actions.check_review_timeout(self, request_id)

    def _on_submit_review_success(self, request_id, review_map, submitted_items, story_text):
        return study_actions.on_submit_review_success(self, request_id, review_map, submitted_items, story_text)

    def _on_submit_review_failed(self, request_id, message):
        return study_actions.on_submit_review_failed(self, request_id, message)

    def _submit_study_answers(self):
        return study_actions.submit_study_answers(self)


def main():
    root = tk.Tk()
    VocabularyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

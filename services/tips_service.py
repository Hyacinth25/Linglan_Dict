import json
import os
import random
from datetime import datetime


class TipsService:
    def __init__(self, tips_path, data_dir):
        self.tips_path = tips_path
        self.seen_path = os.path.join(data_dir, "seen_tips.json")
        self.special_path = os.path.join(data_dir, "special_tips.json")
        self._tips_cache = None
        self._special_cache = None
        self._seen_cache = None

    def _load_tips(self):
        if self._tips_cache is not None:
            return self._tips_cache
        try:
            with open(self.tips_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            lines = ["灵儿正在努力连接魔法世界，等我一下下哦... (〃'▽'〃)"]
        self._tips_cache = lines
        return lines

    def _load_special(self):
        if self._special_cache is not None:
            return self._special_cache
        try:
            with open(self.special_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"special_tips": []}
        self._special_cache = data.get("special_tips", [])
        return self._special_cache

    def _load_seen(self):
        if self._seen_cache is not None:
            return self._seen_cache
        try:
            with open(self.seen_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"seen": [], "special_seen": []}
        self._seen_cache = data
        return data

    def _save_seen(self, data):
        os.makedirs(os.path.dirname(self.seen_path) or ".", exist_ok=True)
        with open(self.seen_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._seen_cache = data

    def mark_seen(self, tip_text):
        data = self._load_seen()
        seen = data.get("seen", [])
        if tip_text not in seen:
            seen.append(tip_text)
            data["seen"] = seen
            self._save_seen(data)

    def mark_special_seen(self, tip_text):
        data = self._load_seen()
        seen = data.get("special_seen", [])
        if tip_text not in seen:
            seen.append(tip_text)
            data["special_seen"] = seen
            self._save_seen(data)

    def _check_special_condition(self, condition, context=None):
        now = datetime.now()
        context = context or {}
        if condition == "midnight":
            return 0 <= now.hour < 5
        if condition == "dawn":
            return 5 <= now.hour < 7
        if condition == "spring":
            return 3 <= now.month <= 5
        if condition == "summer":
            return 6 <= now.month <= 8
        if condition == "autumn":
            return 9 <= now.month <= 11
        if condition == "winter":
            return now.month in (12, 1, 2)
        if condition == "new_year":
            return now.month == 1 and now.day == 1
        if condition == "valentine":
            return now.month == 2 and now.day == 14
        if condition == "christmas":
            return now.month == 12 and now.day == 25
        if condition == "halloween":
            return now.month == 10 and now.day == 31
        if condition == "children_day":
            return now.month == 6 and now.day == 1
        if condition == "mid_autumn_approx":
            return now.month == 9 and 10 <= now.day <= 20
        if condition == "spring_festival_approx":
            return now.month == 1 and 20 <= now.day <= 31 or now.month == 2 and 1 <= now.day <= 15
        if condition == "review_1000":
            return context.get("review_words", 0) >= 1000
        if condition == "review_3000":
            return context.get("review_words", 0) >= 3000
        if condition == "review_5000":
            return context.get("review_words", 0) >= 5000
        if condition == "study_streak_7":
            return context.get("streak_days", 0) >= 7
        if condition == "study_streak_3":
            return context.get("streak_days", 0) >= 3
        if condition == "study_streak_30":
            return context.get("streak_days", 0) >= 30
        if condition == "review_2000":
            return context.get("review_words", 0) >= 2000
        if condition == "review_10000":
            return context.get("review_words", 0) >= 10000
        if condition == "weekend":
            return now.weekday() >= 5
        if condition == "monday":
            return now.weekday() == 0
        if condition == "wednesday":
            return now.weekday() == 2
        if condition == "friday":
            return now.weekday() == 4
        if condition == "sunday":
            return now.weekday() == 6
        if condition == "afternoon":
            return 13 <= now.hour < 18
        if condition == "evening":
            return 18 <= now.hour < 22
        if condition == "linglan_birthday":
            return now.month == 4 and now.day == 1
        if condition == "qixi_approx":
            return now.month == 8 and 1 <= now.day <= 20
        if condition == "dragon_boat_approx":
            return now.month == 6 and 1 <= now.day <= 15
        if condition == "lantern_approx":
            return now.month == 2 and 8 <= now.day <= 20
        if condition == "national_day":
            return now.month == 10 and 1 <= now.day <= 7
        if condition == "random_rare":
            return random.random() < 0.03
        if condition == "random_uncommon":
            return random.random() < 0.06
        return False

    def get_special_tip(self, context=None):
        specials = self._load_special()
        seen_data = self._load_seen()
        special_seen = set(seen_data.get("special_seen", []))
        candidates = []
        for sp in specials:
            if sp.get("text", "") in special_seen:
                continue
            if self._check_special_condition(sp.get("condition", ""), context):
                candidates.append(sp)
        if not candidates:
            return None
        chosen = random.choice(candidates)
        self.mark_special_seen(chosen["text"])
        return chosen["text"]

    def get_random_tip(self):
        tips = self._load_tips()
        seen_data = self._load_seen()
        seen = set(seen_data.get("seen", []))
        unseen = [t for t in tips if t not in seen]
        if unseen:
            tip = random.choice(unseen)
        else:
            seen_data["seen"] = []
            self._save_seen(seen_data)
            tip = random.choice(tips)
        self.mark_seen(tip)
        return tip

    def get_all_tips_status(self):
        tips = self._load_tips()
        specials = self._load_special()
        seen_data = self._load_seen()
        seen = set(seen_data.get("seen", []))
        special_seen = set(seen_data.get("special_seen", []))
        result = []
        for t in tips:
            result.append({
                "text": t,
                "seen": t in seen,
                "type": "normal",
                "hint": "",
            })
        for sp in specials:
            result.append({
                "text": sp["text"],
                "seen": sp["text"] in special_seen,
                "type": "special",
                "hint": sp.get("hint", ""),
            })
        return result

    def get_seen_counts(self):
        seen_data = self._load_seen()
        normal_total = len(self._load_tips())
        special_total = len(self._load_special())
        normal_seen = len(seen_data.get("seen", []))
        special_seen = len(seen_data.get("special_seen", []))
        return {
            "normal_seen": normal_seen,
            "normal_total": normal_total,
            "special_seen": special_seen,
            "special_total": special_total,
        }

import os
import re
import sqlite3

from stardict import DictCsv, StarDict


STARDICT_FIELDS = (
    "id",
    "word",
    "sw",
    "phonetic",
    "definition",
    "translation",
    "pos",
    "collins",
    "oxford",
    "tag",
    "bnc",
    "frq",
    "exchange",
    "detail",
    "audio",
)


def _row_to_dict(row):
    if row is None:
        return None
    return {name: row[index] for index, name in enumerate(STARDICT_FIELDS)}


def _common_rank_key(record):
    def as_int(value, fallback):
        try:
            number = int(value)
        except Exception:
            return fallback
        return number if number > 0 else fallback

    return (
        -(as_int(record.get("collins"), 0)),
        -(as_int(record.get("oxford"), 0)),
        as_int(record.get("bnc"), 999999),
        as_int(record.get("frq"), 999999),
        (record.get("word") or "").lower(),
    )


def _edit_distance(left, right, max_distance=2):
    left = (left or "").lower()
    right = (right or "").lower()
    if left == right:
        return 0
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        row_min = current[0]
        for j, right_char in enumerate(right, 1):
            cost = 0 if left_char == right_char else 1
            value = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def _next_prefix(prefix):
    if not prefix:
        return None
    return prefix[:-1] + chr(ord(prefix[-1]) + 1)


class DictionaryService:
    def __init__(self, db_path, source_db_path, csv_path):
        self.db_path = db_path
        self.source_db_path = source_db_path
        self.csv_path = csv_path

    def count_words(self):
        dictionary = StarDict(self.db_path)
        try:
            return dictionary.count()
        finally:
            dictionary.close()

    def initialize_if_empty(self):
        dictionary = StarDict(self.db_path)
        try:
            current = dictionary.count()
            if current > 0:
                self._ensure_personal_tables()
                return current, False
            copied = self._copy_from_source_sqlite()
            if copied <= 0:
                copied = self._copy_from_csv(dictionary)
            if copied <= 0:
                raise FileNotFoundError("未找到可用词库数据源")
            self._ensure_personal_tables()
            return dictionary.count(), True
        finally:
            dictionary.close()

    def _ensure_personal_tables(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS personal_word_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL COLLATE NOCASE,
                    list_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(word, list_name)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_personal_list_name ON personal_word_lists(list_name, word);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS personal_word_progress (
                    word TEXT PRIMARY KEY COLLATE NOCASE,
                    correct_streak INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _copy_from_source_sqlite(self):
        if not os.path.exists(self.source_db_path):
            return 0
        source = sqlite3.connect(self.source_db_path)
        target = sqlite3.connect(self.db_path)
        try:
            source_count = source.execute("SELECT COUNT(*) FROM stardict;").fetchone()[0]
            if source_count <= 0:
                return 0
            target.execute("ATTACH DATABASE ? AS source_db;", (self.source_db_path,))
            target.execute(
                """
                INSERT OR IGNORE INTO stardict
                (word, sw, phonetic, definition, translation, pos, collins, oxford, tag, bnc, frq, exchange, detail, audio)
                SELECT word, sw, phonetic, definition, translation, pos, collins, oxford, tag, bnc, frq, exchange, detail, audio
                FROM source_db.stardict;
                """
            )
            target.commit()
            return target.execute("SELECT COUNT(*) FROM stardict;").fetchone()[0]
        finally:
            target.close()
            source.close()

    def _copy_from_csv(self, dictionary):
        if not os.path.exists(self.csv_path):
            return 0
        source = DictCsv(self.csv_path)
        words = source.dumps()
        if not words:
            return 0
        for word in words:
            data = source.query(word)
            dictionary.register(word, data, False)
        dictionary.commit()
        return dictionary.count()

    def search_word(self, word):
        keyword = (word or "").strip()
        if not keyword:
            return None
        dictionary = StarDict(self.db_path)
        try:
            return dictionary.query(keyword)
        finally:
            dictionary.close()

    def find_lookup_matches(self, word, limit=8):
        keyword = (word or "").strip()
        if not keyword:
            return []
        normalized = re.sub(r"[^A-Za-z'-]", "", keyword).lower().strip("-'")
        if not normalized:
            return []

        select_sql = (
            "SELECT id, word, sw, phonetic, definition, translation, pos, collins, oxford, "
            "tag, bnc, frq, exchange, detail, audio FROM stardict"
        )
        common_order = (
            "ORDER BY collins DESC, oxford DESC, "
            "CASE WHEN bnc IS NULL OR bnc <= 0 THEN 999999 ELSE bnc END, "
            "CASE WHEN frq IS NULL OR frq <= 0 THEN 999999 ELSE frq END, "
            "word COLLATE NOCASE"
        )
        conn = sqlite3.connect(self.db_path)
        candidates = {}

        def add_rows(rows):
            for row in rows:
                record = _row_to_dict(row)
                word_key = (record.get("word") or "").lower()
                if word_key and word_key not in candidates:
                    candidates[word_key] = record

        try:
            exact_row = conn.execute(f"{select_sql} WHERE word = ?;", (keyword,)).fetchone()
            add_rows([exact_row] if exact_row else [])

            variants = set()
            if len(normalized) >= 4:
                for index in range(len(normalized)):
                    variants.add(normalized[:index] + normalized[index + 1:])
                for index in range(len(normalized) - 1):
                    variants.add(
                        normalized[:index]
                        + normalized[index + 1]
                        + normalized[index]
                        + normalized[index + 2:]
                    )
            variants.discard(normalized)
            if variants:
                placeholders = ",".join("?" for _ in variants)
                rows = conn.execute(
                    f"{select_sql} WHERE word IN ({placeholders}) {common_order} LIMIT ?;",
                    tuple(variants) + (max(limit * 2, 12),),
                ).fetchall()
                add_rows(rows)

            prefixes = []
            if len(normalized) <= 2:
                prefixes.append(normalized)
            elif len(normalized) <= 5:
                prefixes.append(normalized[:2])
                prefixes.append(normalized[:1])
            else:
                prefixes.append(normalized[:3])
                prefixes.append(normalized[:2])

            for prefix in dict.fromkeys(prefixes):
                upper = _next_prefix(prefix)
                if not prefix or not upper:
                    continue
                rows = conn.execute(
                    f"{select_sql} WHERE word >= ? AND word < ? {common_order} LIMIT ?;",
                    (prefix, upper, max(limit * 8, 40)),
                ).fetchall()
                add_rows(rows)

            first = normalized[:1]
            upper = _next_prefix(first)
            if first and upper and len(normalized) >= 4:
                rows = conn.execute(
                    f"{select_sql} "
                    "WHERE word >= ? AND word < ? AND length(word) BETWEEN ? AND ? "
                    f"{common_order} LIMIT ?;",
                    (
                        first,
                        upper,
                        max(1, len(normalized) - 2),
                        len(normalized) + 2,
                        max(limit * 18, 120),
                    ),
                ).fetchall()
                add_rows(rows)
        finally:
            conn.close()

        max_distance = 1 if len(normalized) <= 4 else 2
        scored = []
        for record in candidates.values():
            candidate_word = (record.get("word") or "").lower()
            distance = _edit_distance(normalized, candidate_word, max_distance=max_distance)
            starts_with = candidate_word.startswith(normalized) or normalized.startswith(candidate_word)
            if candidate_word != normalized and not starts_with and distance > max_distance:
                continue
            scored.append((record, distance, starts_with))

        scored.sort(
            key=lambda item: (
                0 if (item[0].get("word") or "").lower() == normalized else 1,
                0 if item[2] else 1,
                item[1],
                _common_rank_key(item[0]),
            )
        )
        return [item[0] for item in scored[:limit]]

    def add_word_to_learning(self, word):
        keyword = (word or "").strip()
        if not keyword:
            return False, "请输入单词"
        record = self.search_word(keyword)
        if not record:
            return False, f"词库中没有：{keyword}"
        self._ensure_personal_tables()
        conn = sqlite3.connect(self.db_path)
        try:
            row_word = record.get("word") or keyword
            finished_exists = conn.execute(
                "SELECT 1 FROM personal_word_lists WHERE word = ? AND list_name = 'finished';",
                (row_word,),
            ).fetchone()
            if finished_exists:
                return False, f"该单词已被背诵，不能重复添加：{row_word}"
            learning_exists = conn.execute(
                "SELECT 1 FROM personal_word_lists WHERE word = ? AND list_name = 'learning';",
                (row_word,),
            ).fetchone()
            if learning_exists:
                return False, f"正在背中已存在：{row_word}"
            conn.execute(
                "INSERT OR IGNORE INTO personal_word_lists(word, list_name) VALUES(?, 'learning');",
                (row_word,),
            )
            conn.commit()
            inserted = conn.execute(
                "SELECT 1 FROM personal_word_lists WHERE word = ? AND list_name = 'learning';",
                (row_word,),
            ).fetchone()
            if inserted:
                return True, f"已加入正在背：{row_word}"
            return False, f"添加失败：{row_word}"
        finally:
            conn.close()

    def list_words(self, list_name):
        self._ensure_personal_tables()
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT word FROM personal_word_lists WHERE list_name = ? ORDER BY word COLLATE NOCASE;",
                (list_name,),
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def remove_word_from_list(self, word, list_name):
        keyword = (word or "").strip()
        if not keyword:
            return False
        self._ensure_personal_tables()
        conn = sqlite3.connect(self.db_path)
        try:
            before = conn.total_changes
            conn.execute("DELETE FROM personal_word_lists WHERE word = ? AND list_name = ?;", (keyword, list_name))
            conn.commit()
            return conn.total_changes > before
        finally:
            conn.close()

    def get_learning_words(self, limit):
        self._ensure_personal_tables()
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT word FROM personal_word_lists WHERE list_name = 'learning' ORDER BY RANDOM() LIMIT ?;",
                (limit,),
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def get_word_data(self, word):
        return self.search_word(word)

    def update_streak_and_maybe_finish(self, word, is_correct):
        self._ensure_personal_tables()
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT correct_streak FROM personal_word_progress WHERE word = ?;", (word,)).fetchone()
            current = row[0] if row else 0
            new_value = current + 1 if is_correct else 0
            conn.execute(
                "INSERT OR REPLACE INTO personal_word_progress(word, correct_streak) VALUES(?, ?);",
                (word, new_value),
            )
            moved = False
            if new_value >= 2:
                conn.execute("DELETE FROM personal_word_lists WHERE word = ? AND list_name = 'learning';", (word,))
                conn.execute(
                    "INSERT OR IGNORE INTO personal_word_lists(word, list_name) VALUES(?, 'finished');",
                    (word,),
                )
                moved = True
            conn.commit()
            return new_value, moved
        finally:
            conn.close()

    def import_words_from_txt(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return {"total": 0, "added": 0, "missing": 0, "learned": 0, "existing": 0}
        text = None
        for encoding in ("utf-8", "gbk", "utf-16"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except Exception:
                continue
        if text is None:
            return {"total": 0, "added": 0, "missing": 0, "learned": 0, "existing": 0}
        words = [line.strip() for line in text.splitlines() if line.strip()]
        if not words:
            return {"total": 0, "added": 0, "missing": 0, "learned": 0, "existing": 0}
        self._ensure_personal_tables()
        dictionary = StarDict(self.db_path)
        conn = sqlite3.connect(self.db_path)
        added = 0
        missing = 0
        learned = 0
        existing = 0
        try:
            for word in words:
                record = dictionary.query(word)
                if not record:
                    missing += 1
                    continue
                row_word = record.get("word") or word
                finished_exists = conn.execute(
                    "SELECT 1 FROM personal_word_lists WHERE word = ? AND list_name = 'finished';",
                    (row_word,),
                ).fetchone()
                if finished_exists:
                    learned += 1
                    continue
                before = conn.total_changes
                conn.execute(
                    "INSERT OR IGNORE INTO personal_word_lists(word, list_name) VALUES(?, 'learning');",
                    (row_word,),
                )
                if conn.total_changes > before:
                    added += 1
                else:
                    existing += 1
            conn.commit()
            return {"total": len(words), "added": added, "missing": missing, "learned": learned, "existing": existing}
        finally:
            conn.close()
            dictionary.close()

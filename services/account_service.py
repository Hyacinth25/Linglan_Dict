import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime


class AccountService:
    def __init__(self, db_path, history_dir):
        self.db_path = db_path
        self.history_dir = history_dir

    def _ensure_personal_tables(self, conn):
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personal_word_progress (
                word TEXT PRIMARY KEY COLLATE NOCASE,
                correct_streak INTEGER NOT NULL DEFAULT 0
            );
            """
        )

    def _count_rows(self, conn, table_name):
        return conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]

    def _load_personal_rows(self):
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_personal_tables(conn)
            list_rows = conn.execute(
                "SELECT word, list_name, created_at FROM personal_word_lists ORDER BY list_name, word COLLATE NOCASE;"
            ).fetchall()
            progress_rows = conn.execute(
                "SELECT word, correct_streak FROM personal_word_progress ORDER BY word COLLATE NOCASE;"
            ).fetchall()
            return list_rows, progress_rows
        finally:
            conn.close()

    def _collect_history_files(self):
        history_files = []
        if not os.path.exists(self.history_dir):
            return history_files
        for name in sorted(os.listdir(self.history_dir)):
            if not name.lower().endswith(".md"):
                continue
            full = os.path.join(self.history_dir, name)
            if not os.path.isfile(full):
                continue
            history_files.append((name, full))
        return history_files

    def _clear_history_markdowns(self):
        os.makedirs(self.history_dir, exist_ok=True)
        for name in os.listdir(self.history_dir):
            if not name.lower().endswith(".md"):
                continue
            try:
                os.remove(os.path.join(self.history_dir, name))
            except Exception:
                pass

    def _write_personal_rows(self, word_lists, word_progress):
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_personal_tables(conn)
            conn.execute("DELETE FROM personal_word_lists;")
            conn.execute("DELETE FROM personal_word_progress;")

            for row in word_lists:
                if not isinstance(row, dict):
                    continue
                word = (row.get("word") or "").strip()
                list_name = (row.get("list_name") or "").strip()
                if not word or list_name not in ("learning", "finished"):
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO personal_word_lists(word, list_name) VALUES(?, ?);",
                    (word, list_name),
                )

            for row in word_progress:
                if not isinstance(row, dict):
                    continue
                word = (row.get("word") or "").strip()
                if not word:
                    continue
                try:
                    streak = int(row.get("correct_streak") or 0)
                except Exception:
                    streak = 0
                streak = max(0, streak)
                conn.execute(
                    "INSERT OR REPLACE INTO personal_word_progress(word, correct_streak) VALUES(?, ?);",
                    (word, streak),
                )

            conn.commit()
            lists_count = self._count_rows(conn, "personal_word_lists")
            progress_count = self._count_rows(conn, "personal_word_progress")
        finally:
            conn.close()
        return lists_count, progress_count

    def _extract_personal_rows_from_db_member(self, zf, db_member):
        with tempfile.TemporaryDirectory() as tmpdir:
            imported_db = os.path.join(tmpdir, "imported_vocabulary.db")
            with zf.open(db_member, "r") as src, open(imported_db, "wb") as dst:
                shutil.copyfileobj(src, dst)

            conn = sqlite3.connect(imported_db)
            try:
                tables = set(
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                )
                word_lists = []
                word_progress = []
                if "personal_word_lists" in tables:
                    rows = conn.execute(
                        "SELECT word, list_name, created_at FROM personal_word_lists ORDER BY list_name, word COLLATE NOCASE;"
                    ).fetchall()
                    word_lists = [
                        {"word": row[0], "list_name": row[1], "created_at": row[2]} for row in rows
                    ]
                if "personal_word_progress" in tables:
                    rows = conn.execute(
                        "SELECT word, correct_streak FROM personal_word_progress ORDER BY word COLLATE NOCASE;"
                    ).fetchall()
                    word_progress = [
                        {"word": row[0], "correct_streak": int(row[1] or 0)} for row in rows
                    ]
            finally:
                conn.close()
        return word_lists, word_progress

    def _export_archive(self, output_path, settings_data, env_data):
        list_rows, progress_rows = self._load_personal_rows()
        lists_count = len(list_rows)
        progress_count = len(progress_rows)

        history_files = self._collect_history_files()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = {
                "format": "lily-vocabulary-account",
                "version": 3,
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "settings": dict(settings_data or {}),
                "env": {
                    "API_KEY": (env_data or {}).get("API_KEY", ""),
                    "BASE_URL": (env_data or {}).get("BASE_URL", ""),
                },
                "history_dir": "study_stories",
                "history_files": [name for name, _ in history_files],
                "word_lists": [
                    {"word": row[0], "list_name": row[1], "created_at": row[2]} for row in list_rows
                ],
                "word_progress": [
                    {"word": row[0], "correct_streak": int(row[1] or 0)} for row in progress_rows
                ],
            }
            manifest_path = os.path.join(tmpdir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(manifest_path, arcname="manifest.json")
                for name, full in history_files:
                    zf.write(full, arcname=f"study_stories/{name}")

        return {
            "lists_count": lists_count,
            "progress_count": progress_count,
            "history_count": len(history_files),
        }

    def _import_archive(self, input_path):
        with zipfile.ZipFile(input_path, "r") as zf:
            try:
                manifest_raw = zf.read("manifest.json")
            except KeyError as e:
                raise ValueError("Invalid account file: missing manifest.json") from e

            try:
                manifest = json.loads(manifest_raw.decode("utf-8"))
            except Exception as e:
                raise ValueError("Invalid account file: bad manifest json") from e

            if not isinstance(manifest, dict):
                raise ValueError("Invalid account file: manifest must be object")
            if manifest.get("format") != "lily-vocabulary-account":
                raise ValueError("Invalid account file format")

            word_lists = manifest.get("word_lists")
            word_progress = manifest.get("word_progress")
            if isinstance(word_lists, list) and isinstance(word_progress, list):
                imported_word_lists = word_lists
                imported_word_progress = word_progress
            else:
                # Compatibility for old archive format(v2) that stored full vocabulary.db.
                db_member = manifest.get("db_file") or "vocabulary.db"
                if db_member in zf.namelist():
                    imported_word_lists, imported_word_progress = self._extract_personal_rows_from_db_member(zf, db_member)
                else:
                    imported_word_lists, imported_word_progress = [], []

            lists_count, progress_count = self._write_personal_rows(imported_word_lists, imported_word_progress)

            history_prefix = (manifest.get("history_dir") or "study_stories").strip("/\\")
            history_prefix = (history_prefix + "/") if history_prefix else ""
            self._clear_history_markdowns()
            imported_histories = 0
            for member in zf.namelist():
                normalized = member.replace("\\", "/")
                if history_prefix and not normalized.startswith(history_prefix):
                    continue
                if not normalized.lower().endswith(".md"):
                    continue
                file_name = os.path.basename(normalized)
                if not file_name:
                    continue
                target = os.path.join(self.history_dir, file_name)
                with zf.open(member, "r") as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                imported_histories += 1

        return {
            "settings": manifest.get("settings") or {},
            "env": manifest.get("env") or {},
            "lists_count": lists_count,
            "progress_count": progress_count,
            "history_count": imported_histories,
        }

    def _import_legacy_json(self, input_path):
        with open(input_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, dict):
            raise ValueError("Invalid account file")
        if payload.get("format") != "lily-vocabulary-account":
            raise ValueError("Invalid account file format")

        settings = payload.get("settings") or {}
        env = payload.get("env") or {}
        word_lists = payload.get("word_lists") or []
        word_progress = payload.get("word_progress") or []
        histories = payload.get("study_histories") or []

        lists_count, progress_count = self._write_personal_rows(word_lists, word_progress)

        self._clear_history_markdowns()
        imported_histories = 0
        for row in histories:
            if not isinstance(row, dict):
                continue
            name = os.path.basename((row.get("name") or "").strip())
            content = row.get("content")
            if not name or not isinstance(content, str):
                continue
            if not name.lower().endswith(".md"):
                name = name + ".md"
            output_path = os.path.join(self.history_dir, name)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            imported_histories += 1

        return {
            "settings": settings,
            "env": env,
            "lists_count": lists_count,
            "progress_count": progress_count,
            "history_count": imported_histories,
        }

    def export_account(self, output_path, settings_data, env_data):
        return self._export_archive(output_path, settings_data, env_data)

    def import_account(self, input_path):
        if zipfile.is_zipfile(input_path):
            return self._import_archive(input_path)
        return self._import_legacy_json(input_path)

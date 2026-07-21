import json
import os
import uuid
from datetime import datetime


class CompetitionService:
    def __init__(self, data_path):
        self.data_path = data_path

    def _ensure_file(self):
        if not os.path.exists(self.data_path):
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)

    def _load(self):
        self._ensure_file()
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"records": []}
        records = data.get("records")
        if not isinstance(records, list):
            records = []
        return records

    def _save(self, records):
        os.makedirs(os.path.dirname(self.data_path) or ".", exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump({"records": records}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _today_str():
        now = datetime.now()
        return f"{now.year}/{now.month}/{now.day}"

    def _recompute_ranks(self, records):
        groups = {}
        for record in records:
            key = (record.get("group_count"), record.get("start_group"))
            groups.setdefault(key, []).append(record)
        for key, items in groups.items():
            items.sort(key=lambda r: (r.get("elapsed_seconds", float("inf")), r.get("created_ts", 0)))
            total = len(items)
            for index, item in enumerate(items):
                item["rank"] = index + 1
                existing_remark = (item.get("remark") or "").strip()
                is_split = item.get("is_split", False)
                split_part = ""
                if is_split and existing_remark.endswith("L"):
                    split_part = existing_remark
                    existing_remark = ""
                if existing_remark:
                    continue
                suffix = ""
                if total == 1:
                    suffix = "begin"
                elif item["rank"] == 1:
                    same_day_others = [
                        r for r in items
                        if r.get("id") != item.get("id") and r.get("created_at") == item.get("created_at")
                    ]
                    if not same_day_others:
                        suffix = "PB-First"
                    else:
                        suffix = "PB"
                if split_part and suffix:
                    item["remark"] = split_part + " | " + suffix
                elif split_part:
                    item["remark"] = split_part
                elif suffix:
                    item["remark"] = suffix
                else:
                    item["remark"] = ""
        return records

    def list_records(self):
        records = self._load()
        records.sort(
            key=lambda r: (
                -(r.get("group_count") or 0),
                r.get("elapsed_seconds", float("inf")),
                r.get("created_ts", 0),
            )
        )
        return records

    def add_record(self, group_count, start_group, elapsed_seconds):
        records = self._load()
        end_group = start_group + group_count - 1
        created_ts = datetime.now().timestamp()
        record = {
            "id": uuid.uuid4().hex,
            "group_count": int(group_count),
            "start_group": int(start_group),
            "end_group": int(end_group),
            "elapsed_seconds": float(elapsed_seconds),
            "created_at": self._today_str(),
            "created_ts": created_ts,
            "rank": 0,
            "remark": "",
        }
        records.append(record)
        self._recompute_ranks(records)
        self._save(records)
        return record

    def add_record_with_splits(self, group_count, start_group, split_elapsed_list):
        records = self._load()
        total_id = uuid.uuid4().hex
        created_ts = datetime.now().timestamp()
        today = self._today_str()
        split_records_data = []
        for idx, elapsed in enumerate(split_elapsed_list):
            list_num = start_group + idx
            split_id = uuid.uuid4().hex
            remark = f"{group_count}L"
            split_records_data.append({
                "id": split_id,
                "group_count": 1,
                "start_group": list_num,
                "end_group": list_num,
                "elapsed_seconds": float(elapsed),
                "created_at": today,
                "created_ts": created_ts,
                "rank": 0,
                "remark": remark,
                "is_split": True,
                "split_of": total_id,
            })
            records.append(split_records_data[-1])
        total_elapsed = sum(float(e) for e in split_elapsed_list)
        end_group = start_group + group_count - 1
        total_record = {
            "id": total_id,
            "group_count": int(group_count),
            "start_group": int(start_group),
            "end_group": int(end_group),
            "elapsed_seconds": total_elapsed,
            "created_at": today,
            "created_ts": created_ts,
            "rank": 0,
            "remark": "",
            "splits": [
                {"list": start_group + idx, "elapsed_seconds": float(e)}
                for idx, e in enumerate(split_elapsed_list)
            ],
        }
        records.append(total_record)
        self._recompute_ranks(records)
        self._save(records)
        return total_record

    def get_split_records(self, total_record_id):
        records = self._load()
        return [r for r in records if r.get("split_of") == total_record_id]

    def delete_record(self, record_id):
        records = self._load()
        split_ids = {r.get("id") for r in records if r.get("split_of") == record_id}
        filtered = [r for r in records if r.get("id") != record_id and r.get("split_of") != record_id]
        if len(filtered) == len(records):
            return False
        self._recompute_ranks(filtered)
        self._save(filtered)
        return True

    def export_to_excel(self, file_path):
        try:
            from openpyxl import Workbook
        except Exception as e:
            raise RuntimeError(f"需要 openpyxl 才能导出 Excel：{e}")
        records = self.list_records()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "竞赛记录"
        total_ranks = self.compute_total_ranks_map(records)
        sheet.append(["单词组", "用时", "排名", "总榜排名", "时间", "等级", "备注"])
        for record in records:
            tr_entry = total_ranks.get(record.get("id"), (0, 0))
            total_rank_str = f"{tr_entry[0]}"
            sheet.append(
                [
                    f"List {record.get('start_group')}-{record.get('end_group')}",
                    self.format_elapsed(record.get("elapsed_seconds", 0.0)),
                    self.format_rank(record.get("rank", 0)),
                    total_rank_str,
                    record.get("created_at", ""),
                    self.get_grade(record.get("elapsed_seconds", 0.0), record.get("group_count", 1)),
                    record.get("remark", ""),
                ]
            )
        widths = [22, 14, 8, 10, 14, 8, 10]
        for index, width in enumerate(widths, start=1):
            sheet.column_dimensions[chr(ord("A") + index - 1)].width = width
        workbook.save(file_path)
        return len(records)

    def get_today_total_seconds(self):
        records = self._load()
        today = self._today_str()
        return sum(
            r.get("elapsed_seconds", 0.0)
            for r in records
            if r.get("created_at") == today and not r.get("is_split")
        )

    def get_today_review_count(self):
        records = self._load()
        today = self._today_str()
        return sum(
            r.get("group_count", 0)
            for r in records
            if r.get("created_at") == today and not r.get("is_split")
        )

    def compute_total_ranks_map(self, records=None):
        if records is None:
            records = self._load()
        groups = {}
        for r in records:
            key = r.get("group_count")
            groups.setdefault(key, []).append(r)
        rank_map = {}
        for key, items in groups.items():
            items.sort(key=lambda r: (r.get("elapsed_seconds", float("inf")), r.get("created_ts", 0)))
            for idx, item in enumerate(items):
                rank_map[item.get("id")] = (idx + 1, len(items))
        return rank_map

    def get_total_rank_and_count(self, record_id, group_count):
        records = self._load()
        same_count = [r for r in records if r.get("group_count") == group_count]
        same_count.sort(key=lambda r: (r.get("elapsed_seconds", float("inf")), r.get("created_ts", 0)))
        total = len(same_count)
        for idx, r in enumerate(same_count):
            if r.get("id") == record_id:
                return idx + 1, total
        return 0, total

    def get_previous_best(self, group_count, start_group, exclude_id):
        records = self._load()
        same_group = [
            r for r in records
            if r.get("group_count") == group_count
            and r.get("start_group") == start_group
            and r.get("id") != exclude_id
        ]
        if not same_group:
            return None
        same_group.sort(key=lambda r: (r.get("elapsed_seconds", float("inf")), r.get("created_ts", 0)))
        return same_group[0]

    @staticmethod
    def _grade_scale(group_count):
        gc = int(group_count)
        if gc <= 1:
            return 1.0
        if gc == 5:
            return 1.2
        if gc == 10:
            return 1.5
        if gc == 25:
            return 1.7
        return 1.8

    @staticmethod
    def get_grade(elapsed_seconds, group_count):
        avg = float(elapsed_seconds) / max(int(group_count), 1)
        scale = CompetitionService._grade_scale(group_count)
        if avg < 30 * scale:
            return "Iridium"
        elif avg < 38 * scale:
            return "Gold"
        elif avg < 48 * scale:
            return "Silver"
        elif avg < 60 * scale:
            return "Copper"
        return "-"

    @staticmethod
    def format_rank(rank):
        try:
            n = int(rank)
        except Exception:
            return str(rank)
        if n == 1:
            return "1st"
        if n == 2:
            return "2nd"
        if n == 3:
            return "3rd"
        return str(n)

    @staticmethod
    def format_elapsed(seconds):
        try:
            total = float(seconds)
        except Exception:
            total = 0.0
        if total < 0:
            total = 0.0
        minutes = int(total // 60)
        remainder = total - minutes * 60
        return f"{minutes:02d}:{remainder:06.3f}"

"""Restore PB/PB-First/begin remarks that were cleared by old _recompute_ranks logic.

Simulates the historical order of record creation (by created_ts) for each group,
re-derives what each record's remark SHOULD have been at the time it was created,
and applies it — only to records with empty remarks, preserving existing ones.
"""
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "competition_records.json")


def restore():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        print("No records found.")
        return

    # Group by (group_count, start_group)
    groups = {}
    for r in records:
        key = (r.get("group_count"), r.get("start_group"))
        groups.setdefault(key, []).append(r)

    restored_count = 0

    for key, items in groups.items():
        # Sort chronologically by creation time
        items.sort(key=lambda r: r.get("created_ts", 0))

        history = []  # records added so far in this group (chronological order)

        for r in items:
            # Add this record to history
            history.append(r)

            # Skip if already has a remark
            if r.get("remark", "").strip():
                continue

            # Re-sort history by elapsed time to determine rank at this moment
            sorted_history = sorted(history, key=lambda x: (x.get("elapsed_seconds", float("inf")), x.get("created_ts", 0)))
            rank = sorted_history.index(r) + 1

            total_at_creation = len(history)

            if total_at_creation == 1:
                r["remark"] = "begin"
            elif rank == 1:
                same_day_others = [
                    h for h in history
                    if h.get("id") != r.get("id") and h.get("created_at") == r.get("created_at")
                ]
                if not same_day_others:
                    r["remark"] = "PB-First"
                else:
                    r["remark"] = "PB"
            # else: leave empty

            if r.get("remark"):
                restored_count += 1

    # Recompute current ranks
    for key, items in groups.items():
        items.sort(key=lambda r: (r.get("elapsed_seconds", float("inf")), r.get("created_ts", 0)))
        for idx, r in enumerate(items):
            r["rank"] = idx + 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Restored {restored_count} remark(s).")


if __name__ == "__main__":
    restore()

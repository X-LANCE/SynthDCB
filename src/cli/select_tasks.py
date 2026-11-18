"""Select an offline task subset without calling a model or changing the pool."""

import argparse
from pathlib import Path

from src.utils import format_json, load_json, load_jsonl, parse_json, write_json, write_jsonl
from src.evaluation.selection import select_tasks


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--task_list", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--ratios", type=Path, required=True, help="JSON map of family.subtype to nonnegative weight")
    parser.add_argument("--outcome_ratios", type=Path, help="JSON map of family.subtype to outcome weights (feasible, infeasible.REASON_CODE); defaults to pool proportions")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--eligible_ids", type=Path)
    parser.add_argument("--excluded_ids", type=Path)
    parser.add_argument("--output_root", type=Path, required=True)
    args = parser.parse_args()
    def ids(path):
        if path is None:
            return None
        payload = path.read_text(encoding="utf-8")
        values = parse_json(payload) if payload.lstrip().startswith("[") else payload.splitlines()
        return set(value.strip() for value in values if value.strip())
    rows = load_jsonl(args.task_list)
    report = select_tasks(rows, count=args.count, ratios=load_json(args.ratios), outcome_ratios=load_json(args.outcome_ratios) if args.outcome_ratios else None, seed=args.seed, eligible=ids(args.eligible_ids), excluded=ids(args.excluded_ids) or set())
    args.output_root.mkdir(parents=True, exist_ok=False)
    (args.output_root / "selected_ids.txt").write_text("".join(f"{task_id}\n" for task_id in report["selected_ids"]), encoding="utf-8")
    write_json(args.output_root / "selection_report.json", report)
    selected = set(report["selected_ids"])
    write_jsonl(args.output_root / "task_list.jsonl", (row for row in rows if row["task_id"] in selected))
    print(format_json({"status": report["status"], "selected": len(selected), "shortages": report["shortages"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

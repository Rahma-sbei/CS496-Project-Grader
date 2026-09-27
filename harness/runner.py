"""
harness/runner.py — runs the harness with one command, writes one row per
item plus a summary to /results, per the slides' requirement.

Modes:
  validate-judge     Runs the judge on the golden set, compares to
                     reconciled_label. Use this BEFORE trusting the judge.
  run-system         Runs the system on fresh briefs, then the judge grades
                     the output. This is the real measurement of the system.
  check-judge-bias   Runs the verbosity-bias and order-bias probes required
                     by the slides' judge reliability report.

Usage:
  python -m harness.runner validate-judge --judge-version v1
  python -m harness.runner run-system --system-version v1 --judge-version v1
  python -m harness.runner check-judge-bias --judge-version v1 --limit 20

FIXES vs the original:
  - A crash/exception on one item no longer takes down the whole run or
    loses already-computed rows: every item is wrapped in its own
    try/except, and results are written even if the run is interrupted.
  - The console now prints WHY an item errored, not just the word ERROR.
"""
import json
import argparse
import traceback
from datetime import datetime, timezone
from pathlib import Path

from harness.judge import judge_email, compare_to_reconciled, verbosity_bias_check, order_bias_check
from harness.system import write_email
from harness.scorer import score_judge_validation, score_system_run

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
GOLDEN_SET_PATH = ROOT / "data" / "golden_set.jsonl"
BRIEFS_PATH = ROOT / "data" / "briefs.jsonl"


def load_jsonl(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(
            f"Expected data file not found: {path}\n"
            f"(Check you're running from the repo root and the file has been committed.)"
        )
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _short_error(verdict: dict) -> str:
    err = verdict.get("error", "")
    return (err[:160] + "...") if len(err) > 160 else err


def run_validate_judge(judge_version: str, split: str, limit: int = None):
    items = load_jsonl(GOLDEN_SET_PATH)
    if split != "all":
        items = [it for it in items if it["split"] == split]
    if limit:
        items = items[:limit]

    rows = []
    print(f"[validate-judge] judge={judge_version} split={split} n={len(items)}")
    try:
        for i, item in enumerate(items, 1):
            try:
                verdict = judge_email(item["brief"], item["candidate_email"], judge_version)
                comparison = compare_to_reconciled(verdict, item["reconciled_label"])
            except Exception as e:  # per-item safety net — never lose the whole run over one bad item
                verdict = {"error": f"{type(e).__name__}: {e}"}
                comparison = {"error": verdict["error"]}
                print(f"  [{i}/{len(items)}] {item.get('id', '?')}: UNEXPECTED ERROR")
                traceback.print_exc()
            rows.append({
                "id": item["id"],
                "input": item["brief"],
                "output": item["candidate_email"],
                "violation_injected": item["violation_injected"],
                "judge_verdict": verdict,
                "reconciled_label": item["reconciled_label"],
                "comparison": comparison,
            })
            if "error" in verdict:
                print(f"  [{i}/{len(items)}] {item['id']}: ERROR - {_short_error(verdict)}")
            else:
                print(f"  [{i}/{len(items)}] {item['id']}: score_exact={comparison.get('score_exact')}")
    finally:
        # Always write whatever we have, even on Ctrl-C or an unexpected
        # crash outside the per-item guard above.
        if rows:
            summary = score_judge_validation(rows)
            summary["judge_version"] = judge_version
            summary["split"] = split
            _write_results("judge_validation", judge_version, rows, summary)
            return summary
        print("No rows were produced — nothing written.")
        return None


def run_system(system_version: str, judge_version: str, limit: int = None):
    briefs = load_jsonl(BRIEFS_PATH)
    if limit:
        briefs = briefs[:limit]

    rows = []
    print(f"[run-system] system={system_version} judge={judge_version} n={len(briefs)}")
    try:
        for i, b in enumerate(briefs, 1):
            try:
                system_output = write_email(b["brief"], system_version)
                if "error" in system_output:
                    rows.append({"id": b["id"], "input": b["brief"], "system_output": system_output,
                                 "judge_verdict": {"error": "skipped, system failed"}})
                    print(f"  [{i}/{len(briefs)}] {b['id']}: SYSTEM ERROR - {_short_error(system_output)}")
                    continue
                verdict = judge_email(b["brief"], system_output["email"], judge_version)
            except Exception as e:
                system_output = {"error": f"{type(e).__name__}: {e}"}
                verdict = {"error": "skipped, unexpected exception"}
                print(f"  [{i}/{len(briefs)}] {b.get('id', '?')}: UNEXPECTED ERROR")
                traceback.print_exc()
                rows.append({"id": b["id"], "input": b["brief"], "system_output": system_output,
                             "judge_verdict": verdict})
                continue
            rows.append({
                "id": b["id"],
                "input": b["brief"],
                "system_output": system_output,
                "judge_verdict": verdict,
            })
            if "error" in verdict:
                print(f"  [{i}/{len(briefs)}] {b['id']}: ERROR - {_short_error(verdict)}")
            else:
                print(f"  [{i}/{len(briefs)}] {b['id']}: score={verdict.get('overall_score')}")
    finally:
        if rows:
            summary = score_system_run(rows)
            summary["system_version"] = system_version
            summary["judge_version"] = judge_version
            _write_results("system_run", f"{system_version}_judge-{judge_version}", rows, summary)
            return summary
        print("No rows were produced — nothing written.")
        return None


def run_check_judge_bias(judge_version: str, limit: int = 20):
    items = load_jsonl(GOLDEN_SET_PATH)[:limit]
    rows = []
    print(f"[check-judge-bias] judge={judge_version} n={len(items)}")
    for i, item in enumerate(items, 1):
        try:
            verbosity = verbosity_bias_check(item["brief"], item["candidate_email"], judge_version)
            order = order_bias_check(item["brief"], item["candidate_email"], judge_version)
        except Exception as e:
            verbosity = {"error": f"{type(e).__name__}: {e}"}
            order = {"error": f"{type(e).__name__}: {e}"}
            traceback.print_exc()
        rows.append({"id": item["id"], "verbosity_bias": verbosity, "order_bias": order})
        v_flag = verbosity.get("score_increased_from_padding")
        o_flag = order.get("score_changed")
        print(f"  [{i}/{len(items)}] {item['id']}: padding_increased_score={v_flag} order_changed_score={o_flag}")

    n = len(rows)
    v_ok = [r["verbosity_bias"] for r in rows if "error" not in r["verbosity_bias"]]
    o_ok = [r["order_bias"] for r in rows if "error" not in r["order_bias"]]
    summary = {
        "judge_version": judge_version,
        "n_items": n,
        "n_verbosity_errors": n - len(v_ok),
        "verbosity_bias_rate": sum(1 for v in v_ok if v["score_increased_from_padding"]) / len(v_ok) if v_ok else None,
        "n_order_errors": n - len(o_ok),
        "order_bias_rate": sum(1 for o in o_ok if o["score_changed"]) / len(o_ok) if o_ok else None,
    }
    _write_results("judge_bias", judge_version, rows, summary)
    return summary


def _write_results(kind: str, version_tag: str, rows: list, summary: dict):
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = timestamp()
    rows_path = RESULTS_DIR / f"{kind}_{version_tag}_{ts}.jsonl"
    summary_path = RESULTS_DIR / f"{kind}_summary_{version_tag}_{ts}.json"
    with open(rows_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n--- SUMMARY ---")
    print(json.dumps(summary, indent=2))
    print(f"\nPer-item results: {rows_path}")
    print(f"Summary:          {summary_path}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("validate-judge")
    p1.add_argument("--judge-version", default="v1")
    p1.add_argument("--split", default="all", choices=["all", "dev", "test"])
    p1.add_argument("--limit", type=int, default=None)

    p2 = sub.add_parser("run-system")
    p2.add_argument("--system-version", default="v1")
    p2.add_argument("--judge-version", default="v1")
    p2.add_argument("--limit", type=int, default=None)

    p3 = sub.add_parser("check-judge-bias")
    p3.add_argument("--judge-version", default="v1")
    p3.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    if args.command == "validate-judge":
        run_validate_judge(args.judge_version, args.split, args.limit)
    elif args.command == "run-system":
        run_system(args.system_version, args.judge_version, args.limit)
    elif args.command == "check-judge-bias":
        run_check_judge_bias(args.judge_version, args.limit)


if __name__ == "__main__":
    main()

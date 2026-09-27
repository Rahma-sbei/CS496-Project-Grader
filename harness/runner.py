"""
harness/runner.py — runs the harness with one command, writes one row per
item plus a summary to /results, per the slides' requirement.

Modes:
  validate-judge     Runs the judge on the golden set, compares to
                     reconciled_label. Use this BEFORE trusting the judge.
  run-system         Runs the system on fresh briefs, then the judge grades
                     the output. This is the real measurement of the system.
  check-judge-bias   Runs the verbosity-bias (padding) and position-bias
                     (swap A/B) probes for the judge reliability report.
  label-agreement    Agreement between the two human labellers (no API call).

Usage:
  python -m harness.runner label-agreement
  python -m harness.runner validate-judge --judge-version v3 --split dev
  python -m harness.runner run-system --system-version v1 --judge-version v3 --split dev
  python -m harness.runner check-judge-bias --judge-version v3 --pairwise-version v1

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

from harness.judge import judge_email, compare_to_reconciled, verbosity_bias_check, position_bias_check
from harness.system import write_email
from harness.llm_client import DAILY_LIMIT_MARKER
from harness.scorer import score_judge_validation, score_system_run, score_judge_bias, score_labeller_agreement

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


def _daily_limit_hit(*results) -> bool:
    """True if any call hit the provider's per-day limit: stop the run, the
    rest would fail too. Rows so far are still written."""
    if any(DAILY_LIMIT_MARKER in str(r.get("error", "")) for r in results if isinstance(r, dict)):
        print(f"\nSTOPPED: daily token limit reached. Results so far are saved. "
              f"Wait for the limit to reset (see the error for the time) and run again.")
        return True
    return False


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
                "score": verdict.get("overall_score"),
                "reason": verdict.get("reason") or verdict.get("error"),
                "human_score": item["reconciled_label"]["overall_score"],
                "judge_verdict": verdict,
                "reconciled_label": item["reconciled_label"],
                "comparison": comparison,
            })
            if "error" in verdict:
                print(f"  [{i}/{len(items)}] {item['id']}: ERROR - {_short_error(verdict)}")
            else:
                print(f"  [{i}/{len(items)}] {item['id']}: score_exact={comparison.get('score_exact')}")
            if _daily_limit_hit(verdict):
                break
    finally:
        # Always write whatever we have, even on Ctrl-C or an unexpected
        # crash outside the per-item guard above.
        if rows:
            summary = score_judge_validation(rows)
            summary["judge_version"] = judge_version
            summary["split"] = split
            _write_results("judge_validation", judge_version, rows, summary)
        else:
            summary = None
            print("No rows were produced — nothing written.")
    return summary


def run_system(system_version: str, judge_version: str, split: str, limit: int = None):
    briefs = load_jsonl(BRIEFS_PATH)
    if split != "all":
        briefs = [b for b in briefs if b["split"] == split]
    if limit:
        briefs = briefs[:limit]

    rows = []
    print(f"[run-system] system={system_version} judge={judge_version} split={split} n={len(briefs)}")
    try:
        for i, b in enumerate(briefs, 1):
            try:
                system_output = write_email(b["brief"], system_version)
                if "error" in system_output:
                    rows.append({"id": b["id"], "input": b["brief"], "output": None, "score": None,
                                 "reason": system_output["error"], "system_output": system_output,
                                 "judge_verdict": {"error": "skipped, system failed"}})
                    print(f"  [{i}/{len(briefs)}] {b['id']}: SYSTEM ERROR - {_short_error(system_output)}")
                    if _daily_limit_hit(system_output):
                        break
                    continue
                verdict = judge_email(b["brief"], system_output["email"], judge_version)
            except Exception as e:
                system_output = {"error": f"{type(e).__name__}: {e}"}
                verdict = {"error": "skipped, unexpected exception"}
                print(f"  [{i}/{len(briefs)}] {b.get('id', '?')}: UNEXPECTED ERROR")
                traceback.print_exc()
                rows.append({"id": b["id"], "input": b["brief"], "output": None, "score": None,
                             "reason": system_output["error"], "system_output": system_output,
                             "judge_verdict": verdict})
                continue
            rows.append({
                "id": b["id"],
                "input": b["brief"],
                "output": system_output["email"],
                "score": verdict.get("overall_score"),
                "reason": verdict.get("reason") or verdict.get("error"),
                "system_output": system_output,
                "judge_verdict": verdict,
            })
            if "error" in verdict:
                print(f"  [{i}/{len(briefs)}] {b['id']}: ERROR - {_short_error(verdict)}")
            else:
                print(f"  [{i}/{len(briefs)}] {b['id']}: score={verdict.get('overall_score')}")
            if _daily_limit_hit(verdict):
                break
    finally:
        if rows:
            summary = score_system_run(rows)
            summary["system_version"] = system_version
            summary["judge_version"] = judge_version
            summary["split"] = split
            _write_results("system_run", f"{system_version}_judge-{judge_version}_{split}", rows, summary)
        else:
            summary = None
            print("No rows were produced — nothing written.")
    return summary


def _pairs_for_position_bias(items: list) -> list:
    """(brief, better_email, worse_email, ids) for every two items that share a
    brief and have different human scores."""
    by_brief = {}
    for it in items:
        by_brief.setdefault(json.dumps(it["brief"], sort_keys=True), []).append(it)
    pairs = []
    for group in by_brief.values():
        for i, x in enumerate(group):
            for y in group[i + 1:]:
                sx, sy = x["reconciled_label"]["overall_score"], y["reconciled_label"]["overall_score"]
                if sx == sy:
                    continue
                better, worse = (x, y) if sx > sy else (y, x)
                pairs.append((better, worse))
    return pairs


def run_check_judge_bias(judge_version: str, pairwise_version: str, split: str, limit: int = None):
    items = load_jsonl(GOLDEN_SET_PATH)
    if split != "all":
        items = [it for it in items if it["split"] == split]
    verbosity_items = items[:limit] if limit else items
    pairs = _pairs_for_position_bias(items)
    pairs = pairs[:limit] if limit else pairs

    rows = []
    print(f"[check-judge-bias] judge={judge_version} pairwise={pairwise_version} split={split} "
          f"verbosity_items={len(verbosity_items)} position_pairs={len(pairs)}")
    try:
        for i, item in enumerate(verbosity_items, 1):
            try:
                v = verbosity_bias_check(item["brief"], item["candidate_email"], judge_version)
            except Exception as e:
                v = {"error": f"{type(e).__name__}: {e}"}
                traceback.print_exc()
            rows.append({"id": item["id"], "probe": "verbosity", "input": item["brief"],
                         "output": item["candidate_email"], "score": v.get("score_delta"),
                         "reason": v.get("error") or f"original={v.get('original_score')} padded={v.get('padded_score')}",
                         "verbosity_bias": v})
            print(f"  [verbosity {i}/{len(verbosity_items)}] {item['id']}: "
                  f"{v.get('error') or 'delta=' + str(v.get('score_delta'))}")
            if _daily_limit_hit(v):
                break
        for i, (better, worse) in enumerate(pairs, 1):
            try:
                p = position_bias_check(better["brief"], better["candidate_email"], worse["candidate_email"], pairwise_version)
            except Exception as e:
                p = {"error": f"{type(e).__name__}: {e}"}
                traceback.print_exc()
            pair_id = f"{better['id']}>{worse['id']}"
            rows.append({"id": pair_id, "probe": "position", "input": better["brief"],
                         "output": {"better": better["candidate_email"], "worse": worse["candidate_email"]},
                         "score": None if "error" in p else int(p["agrees_with_humans_both_orders"]),
                         "reason": p.get("error") or p.get("reason_order_1"),
                         "position_bias": p})
            print(f"  [position {i}/{len(pairs)}] {pair_id}: "
                  f"{p.get('error') or 'flipped=' + str(p.get('verdict_flipped'))}")
            if _daily_limit_hit(p):
                break
    finally:
        if rows:
            summary = score_judge_bias(rows)
            summary.update({"judge_version": judge_version, "pairwise_version": pairwise_version, "split": split})
            _write_results("judge_bias", f"{judge_version}_pairwise-{pairwise_version}_{split}", rows, summary)
        else:
            summary = None
    return summary


def run_label_agreement():
    items = load_jsonl(GOLDEN_SET_PATH)
    summary = score_labeller_agreement(items)
    dropped_path = ROOT / "data" / "dropped_items.jsonl"
    dropped = load_jsonl(dropped_path) if dropped_path.exists() else []
    summary["n_dropped"] = len(dropped)
    summary["dropped_reasons"] = [{"id": d["id"], "reason": d["reason"]} for d in dropped]
    rows = [{"id": it["id"], "labeler_1": it["human_labels"]["labeler_1"], "labeler_2": it["human_labels"]["labeler_2"],
             "reconciled_label": it["reconciled_label"]} for it in items]
    _write_results("label_agreement", "golden", rows, summary)
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
    p2.add_argument("--split", default="dev", choices=["all", "dev", "test"])
    p2.add_argument("--limit", type=int, default=None)

    p3 = sub.add_parser("check-judge-bias")
    p3.add_argument("--judge-version", default="v1")
    p3.add_argument("--pairwise-version", default="v1")
    p3.add_argument("--split", default="dev", choices=["all", "dev", "test"])
    p3.add_argument("--limit", type=int, default=None)

    sub.add_parser("label-agreement")

    args = parser.parse_args()
    if args.command == "validate-judge":
        run_validate_judge(args.judge_version, args.split, args.limit)
    elif args.command == "run-system":
        run_system(args.system_version, args.judge_version, args.split, args.limit)
    elif args.command == "check-judge-bias":
        run_check_judge_bias(args.judge_version, args.pairwise_version, args.split, args.limit)
    elif args.command == "label-agreement":
        run_label_agreement()


if __name__ == "__main__":
    main()

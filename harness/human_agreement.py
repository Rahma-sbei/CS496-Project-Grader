"""
Computes:
  - Human1 vs Human2 agreement (the two independent labelers)
  - LLM judge vs. human-average agreement (Experiment A from the spec)

Run after both data/human_labels/human1.jsonl and human2.jsonl exist, and
after a judge run has produced results/<name>.jsonl.

    python -m harness.human_agreement
    python -m harness.human_agreement --results results/full_run.jsonl
"""
import argparse
import json
from pathlib import Path

from .schema import CRITERIA

REPO_ROOT = Path(__file__).parent.parent
LABELS_DIR = REPO_ROOT / "data" / "human_labels"


def load_labels(path: Path) -> dict:
    labels = {}
    if not path.exists():
        return labels
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                labels[row["id"]] = row
    return labels


def agreement_stats(a: dict, b: dict, common_ids: list) -> dict:
    """Exact-match agreement, overall and per criterion, between two label sets."""
    per_criterion = {c: {"agree": 0, "total": 0} for c in CRITERIA}
    exact_total_match = 0
    disagreements = []

    for item_id in common_ids:
        row_a, row_b = a[item_id], b[item_id]
        item_fully_agrees = True
        for c in CRITERIA:
            per_criterion[c]["total"] += 1
            if row_a[c] == row_b[c]:
                per_criterion[c]["agree"] += 1
            else:
                item_fully_agrees = False
        if item_fully_agrees:
            exact_total_match += 1
        else:
            disagreements.append(
                {
                    "id": item_id,
                    "a": {c: row_a[c] for c in CRITERIA},
                    "b": {c: row_b[c] for c in CRITERIA},
                }
            )

    per_criterion_pct = {
        c: round(100 * v["agree"] / v["total"], 1) if v["total"] else None
        for c, v in per_criterion.items()
    }
    overall_pct = round(100 * exact_total_match / len(common_ids), 1) if common_ids else None

    return {
        "n_items": len(common_ids),
        "exact_full_agreement_count": exact_total_match,
        "exact_full_agreement_pct": overall_pct,
        "agreement_per_criterion_pct": per_criterion_pct,
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
    }


def human_average(row: dict) -> dict:
    return {c: row[c] for c in CRITERIA}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compute human-human and human-judge agreement")
    parser.add_argument("--results", default=None, help="Path to a results/*.jsonl run to compare against humans")
    parser.add_argument("--human1", default=str(LABELS_DIR / "human1.jsonl"))
    parser.add_argument("--human2", default=str(LABELS_DIR / "human2.jsonl"))
    parser.add_argument("--output", default=str(REPO_ROOT / "results" / "human_agreement.json"))
    args = parser.parse_args(argv)

    h1 = load_labels(Path(args.human1))
    h2 = load_labels(Path(args.human2))

    if not h1 or not h2:
        print("Missing human1.jsonl or human2.jsonl - see data/LABELING_GUIDE.md")
        return

    common = sorted(set(h1) & set(h2))
    human_human = agreement_stats(h1, h2, common)

    output = {"human_vs_human": human_human, "judge_vs_human": None}

    if args.results and Path(args.results).exists():
        judge_scores = {}
        with open(args.results) as f:
            for line in f:
                row = json.loads(line)
                if row.get("status") == "ok":
                    judge_scores[row["id"]] = row["scores"]

        # Compare judge against each human individually, then combined pool
        common_j1 = sorted(set(judge_scores) & set(h1))
        common_j2 = sorted(set(judge_scores) & set(h2))
        judge_vs_h1 = agreement_stats(judge_scores, h1, common_j1)
        judge_vs_h2 = agreement_stats(judge_scores, h2, common_j2)
        output["judge_vs_human"] = {
            "judge_vs_human1": judge_vs_h1,
            "judge_vs_human2": judge_vs_h2,
        }

    Path(args.output).parent.mkdir(exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Human1 vs Human2 exact full-rubric agreement: {human_human['exact_full_agreement_pct']}%")
    print(f"Per-criterion agreement: {human_human['agreement_per_criterion_pct']}")
    print(f"Disagreements: {human_human['n_disagreements']} / {human_human['n_items']}")
    print(f"\nWrote full report to {args.output}")


if __name__ == "__main__":
    main()

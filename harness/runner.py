"""
The core evaluation harness. For every item in a dataset file:
  1. Generate an email (generator.py)
  2. Judge the email (judge.py)
  3. Record one result, always - failures are recorded, never dropped
Then computes aggregate statistics and writes everything to JSONL.

This is the module `run_eval.py` (repo root wrapper) calls.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import generator, judge, scorer

REPO_ROOT = Path(__file__).parent.parent
RESULTS_DIR = REPO_ROOT / "results"


def load_dataset(path: str) -> list[dict]:
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def run_item(item: dict, generator_version: str, judge_version: str, model: str = None) -> dict:
    """Runs generation + judging for a single item. Never raises."""
    base = {
        "id": item["id"],
        "input": item,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    gen = generator.generate_email(item, prompt_version=generator_version, model=model)
    base["generation_usage"] = gen["usage"]

    if gen["error"] or not gen["email"]:
        base.update(
            {
                "status": "generation_failed",
                "error": gen["error"] or "empty_generated_email",
                "generated_email": None,
                "scores": None,
                "total_score": None,
                "reason": None,
                "judge_usage": None,
            }
        )
        return base

    base["generated_email"] = gen["email"]

    jr = judge.evaluate_email(item, gen["email"], prompt_version=judge_version, model=model)
    base["judge_usage"] = jr["usage"]

    if jr["error"] or not jr["scores"]:
        base.update(
            {
                "status": "judge_failed",
                "error": jr["error"] or "empty_judge_response",
                "scores": None,
                "total_score": None,
                "reason": None,
            }
        )
        return base

    base.update(
        {
            "status": "ok",
            "error": None,
            "scores": jr["scores"],
            "total_score": jr["scores"]["total_score"],
            "reason": jr["scores"]["reason"],
        }
    )
    return base


def run_evaluation(
    dataset_path: str,
    output_name: str = None,
    generator_version: str = "v1",
    judge_version: str = "v1",
    model: str = None,
    limit: int = None,
    on_progress=None,
) -> dict:
    """
    Runs the full harness over a dataset file and writes results to
    results/<output_name>.jsonl. Returns {"results": [...], "statistics": {...},
    "output_path": str}.
    """
    items = load_dataset(dataset_path)
    if limit:
        items = items[:limit]

    RESULTS_DIR.mkdir(exist_ok=True)
    output_name = output_name or f"run_{int(time.time())}"
    output_path = RESULTS_DIR / f"{output_name}.jsonl"

    results = []
    with open(output_path, "w") as f:
        for i, item in enumerate(items):
            result = run_item(item, generator_version, judge_version, model=model)
            results.append(result)
            f.write(json.dumps(result) + "\n")
            f.flush()
            if on_progress:
                on_progress(i + 1, len(items), result)

    stats = scorer.compute_statistics(results)
    stats_path = RESULTS_DIR / f"{output_name}.stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    return {"results": results, "statistics": stats, "output_path": str(output_path)}


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Run the email-grading evaluation harness")
    parser.add_argument("--dataset", default=str(REPO_ROOT / "data" / "golden_set.jsonl"))
    parser.add_argument("--output", default=None, help="Output name (no extension)")
    parser.add_argument("--generator-version", default="v1")
    parser.add_argument("--judge-version", default="v1")
    parser.add_argument("--model", default=None)
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N items")
    args = parser.parse_args(argv)

    def progress(i, total, result):
        status = result["status"]
        print(f"[{i}/{total}] {result['id']}: {status}")

    outcome = run_evaluation(
        dataset_path=args.dataset,
        output_name=args.output,
        generator_version=args.generator_version,
        judge_version=args.judge_version,
        model=args.model,
        limit=args.limit,
        on_progress=progress,
    )
    print("\n=== Summary ===")
    print(json.dumps(outcome["statistics"], indent=2))
    print(f"\nResults written to {outcome['output_path']}")


if __name__ == "__main__":
    main()

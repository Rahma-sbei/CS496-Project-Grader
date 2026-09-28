"""
Aggregate statistics over a batch of evaluation results. Used by the harness
after a run, and by the backend's /api/statistics endpoint over stored
results.
"""
from collections import defaultdict

from .schema import CRITERIA


def compute_statistics(results: list[dict]) -> dict:
    """
    `results` is a list of per-item result dicts as written by runner.py
    (see the schema in README.md / run_eval output). Items with
    status != "ok" are excluded from score aggregates but counted as failed.
    """
    ok_results = [r for r in results if r.get("status") == "ok"]
    failed_results = [r for r in results if r.get("status") != "ok"]

    total_items = len(results)
    n_ok = len(ok_results)

    stats = {
        "total_items": total_items,
        "evaluated_items": n_ok,
        "failed_items": len(failed_results),
        "failed_ids": [r["id"] for r in failed_results],
        "average_total_score": None,
        "score_distribution": {str(i): 0 for i in range(0, 11)},
        "average_by_criterion": {},
        "average_by_category": {},
        "cost": {
            "total_cost_usd": 0.0,
            "cost_per_item_usd": None,
            "estimated_cost_per_1000": None,
            "estimated_cost_at_100x": None,
        },
    }

    if n_ok == 0:
        return stats

    total_scores = [r["total_score"] for r in ok_results]
    stats["average_total_score"] = round(sum(total_scores) / n_ok, 2)

    for s in total_scores:
        stats["score_distribution"][str(int(s))] += 1

    for c in CRITERIA:
        vals = [r["scores"][c] for r in ok_results]
        stats["average_by_criterion"][c] = round(sum(vals) / len(vals), 2)

    by_cat = defaultdict(list)
    for r in ok_results:
        by_cat[r["input"]["category"]].append(r["total_score"])
    stats["average_by_category"] = {
        cat: round(sum(v) / len(v), 2) for cat, v in by_cat.items()
    }

    total_cost = sum(
        (r.get("generation_usage", {}) or {}).get("cost_usd", 0.0)
        + (r.get("judge_usage", {}) or {}).get("cost_usd", 0.0)
        for r in results
    )
    stats["cost"]["total_cost_usd"] = round(total_cost, 4)
    if total_items > 0:
        cost_per_item = total_cost / total_items
        stats["cost"]["cost_per_item_usd"] = round(cost_per_item, 5)
        stats["cost"]["estimated_cost_per_1000"] = round(cost_per_item * 1000, 2)
        stats["cost"]["estimated_cost_at_100x"] = round(cost_per_item * total_items * 100, 2)

    return stats

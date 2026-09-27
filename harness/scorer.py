"""
harness/scorer.py — turns a list of per-item result rows into the summary
numbers required by the slides: "report as counts and percentages, never
only one summary number." Also aggregates latency/token usage from the
"_meta" block llm_client.call_json now attaches to every successful call —
the slides explicitly require "cost and latency per judged item".
"""
from harness.schema import ALL_RULE_PATHS

# Set this to your Groq model's published per-token price to turn token
# counts into an actual dollar figure for the report's cost model.
USD_PER_1K_PROMPT_TOKENS = 0.0
USD_PER_1K_COMPLETION_TOKENS = 0.0


def _meta_stats(dicts_with_meta: list) -> dict:
    metas = [d.get("_meta") for d in dicts_with_meta if isinstance(d, dict) and d.get("_meta")]
    if not metas:
        return {"n_with_meta": 0}
    latencies = [m["latency_s"] for m in metas if m.get("latency_s") is not None]
    prompt_toks = [m["prompt_tokens"] for m in metas if m.get("prompt_tokens") is not None]
    completion_toks = [m["completion_tokens"] for m in metas if m.get("completion_tokens") is not None]
    total_prompt = sum(prompt_toks) if prompt_toks else None
    total_completion = sum(completion_toks) if completion_toks else None
    est_cost_usd = None
    if total_prompt is not None and total_completion is not None:
        est_cost_usd = (
            total_prompt / 1000 * USD_PER_1K_PROMPT_TOKENS
            + total_completion / 1000 * USD_PER_1K_COMPLETION_TOKENS
        )
    return {
        "n_with_meta": len(metas),
        "avg_latency_s": sum(latencies) / len(latencies) if latencies else None,
        "max_latency_s": max(latencies) if latencies else None,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "estimated_cost_usd": est_cost_usd,
        "estimated_cost_per_1k_items_usd": (est_cost_usd / len(metas) * 1000) if est_cost_usd is not None and metas else None,
    }


def score_judge_validation(rows: list) -> dict:
    """For rows that carry both judge_verdict and reconciled_label (i.e. a
    run of the judge against the golden set): per-rule agreement + score match."""
    n = len(rows)
    n_errors = sum(1 for r in rows if "error" in r["judge_verdict"])
    n_scored = n - n_errors

    rule_hits = {f"{b}.{f}": 0 for b, f in ALL_RULE_PATHS}
    score_exact_hits = 0
    score_within_1_hits = 0

    for r in rows:
        if "error" in r["judge_verdict"]:
            continue
        v, h = r["judge_verdict"], r["reconciled_label"]
        for band, field in ALL_RULE_PATHS:
            rule_hits[f"{band}.{field}"] += int(v[band][field] == h[band][field])
        score_exact_hits += int(v.get("overall_score") == h.get("overall_score"))
        score_within_1_hits += int(abs(v.get("overall_score", 0) - h.get("overall_score", 0)) <= 1)

    return {
        "n_items": n,
        "n_errors": n_errors,
        "n_scored": n_scored,
        "error_reasons": [r["judge_verdict"]["error"] for r in rows if "error" in r["judge_verdict"]][:10],
        "per_rule_agreement": {k: (v / n_scored if n_scored else None) for k, v in rule_hits.items()},
        "score_exact_match_rate": score_exact_hits / n_scored if n_scored else None,
        "score_within_1_rate": score_within_1_hits / n_scored if n_scored else None,
        "judge_latency_and_cost": _meta_stats([r["judge_verdict"] for r in rows]),
    }


def score_system_run(rows: list) -> dict:
    """For rows produced by running the system + judge on fresh briefs
    (no human label exists yet — this is the score the system is being
    measured on, not a judge-validation number)."""
    n = len(rows)
    n_errors = sum(1 for r in rows if "error" in r.get("judge_verdict", {}) or "error" in r.get("system_output", {}))
    scored = [r for r in rows if "error" not in r.get("judge_verdict", {}) and "error" not in r.get("system_output", {})]
    n_scored = len(scored)

    rule_pass_rate = {}
    for band, field in ALL_RULE_PATHS:
        passes = sum(1 for r in scored if r["judge_verdict"][band][field])
        rule_pass_rate[f"{band}.{field}"] = passes / n_scored if n_scored else None

    scores = [r["judge_verdict"]["overall_score"] for r in scored]
    avg_score = sum(scores) / len(scores) if scores else None
    pct_pass_4_or_5 = sum(1 for s in scores if s >= 4) / len(scores) if scores else None

    return {
        "n_items": n,
        "n_errors": n_errors,
        "n_scored": n_scored,
        "average_overall_score": avg_score,
        "pct_scored_4_or_5": pct_pass_4_or_5,
        "per_rule_pass_rate": rule_pass_rate,
        "system_latency_and_cost": _meta_stats([r.get("system_output", {}) for r in rows]),
        "judge_latency_and_cost": _meta_stats([r.get("judge_verdict", {}) for r in rows]),
    }

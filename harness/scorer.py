"""
harness/scorer.py — turns a list of per-item result rows into the summary
numbers required by the slides: "report as counts and percentages, never
only one summary number." Also aggregates latency/token usage from the
"_meta" block llm_client.call_json now attaches to every successful call —
the slides explicitly require "cost and latency per judged item".
"""
from harness.schema import ALL_RULE_PATHS

# Groq on-demand prices, USD per 1M tokens (input, output).
# Source: https://console.groq.com/docs/models (checked 2026-09-27).
# Re-check before the final report; a model missing here gets cost = None.
PRICES_PER_1M = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
    "qwen/qwen3.8-27b": (0.80, 4.00),
}


def _flatten_metas(dicts_with_meta: list) -> list:
    metas = []
    for d in dicts_with_meta:
        m = d.get("_meta") if isinstance(d, dict) else None
        for x in (m if isinstance(m, list) else [m]):
            if x:
                metas.append(x)
    return metas


def _meta_stats(dicts_with_meta: list) -> dict:
    """Latency, tokens and USD cost over every successful call. `n_items` is
    the number of rows (one row may hold several calls, e.g. bias checks)."""
    metas = _flatten_metas(dicts_with_meta)
    if not metas:
        return {"n_calls": 0}
    latencies = [m["latency_s"] for m in metas if m.get("latency_s") is not None]
    prompt_toks = sum(m.get("prompt_tokens") or 0 for m in metas)
    completion_toks = sum(m.get("completion_tokens") or 0 for m in metas)
    cost = 0.0
    for m in metas:
        price = PRICES_PER_1M.get(m.get("model"))
        if price is None:
            cost = None
            break
        cost += (m.get("prompt_tokens") or 0) / 1e6 * price[0] + (m.get("completion_tokens") or 0) / 1e6 * price[1]
    n_items = sum(1 for d in dicts_with_meta if isinstance(d, dict) and d.get("_meta"))
    per_item = cost / n_items if cost is not None and n_items else None
    return {
        "models": sorted({m.get("model") for m in metas if m.get("model")}),
        "n_calls": len(metas),
        "n_items": n_items,
        "avg_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "max_latency_s": max(latencies) if latencies else None,
        "total_prompt_tokens": prompt_toks,
        "total_completion_tokens": completion_toks,
        "avg_tokens_per_item": round((prompt_toks + completion_toks) / n_items, 1) if n_items else None,
        "cost_this_run_usd": round(cost, 6) if cost is not None else None,
        "cost_per_item_usd": round(per_item, 8) if per_item is not None else None,
        "cost_per_1k_items_usd": round(per_item * 1000, 4) if per_item is not None else None,
        # Per-token pricing is linear: 100x the traffic costs 100x. The report
        # must also discuss what does NOT scale linearly (rate limits, latency).
        "cost_per_1k_items_at_100x_volume_usd": round(per_item * 1000 * 100, 2) if per_item is not None else None,
    }


def _count_pct(hits: int, n: int) -> dict:
    return {"count": hits, "n": n, "pct": round(100 * hits / n, 1) if n else None}


def cohen_kappa(a: list, b: list) -> float:
    """Cohen's kappa for two equal-length lists of labels (any hashable values)."""
    n = len(a)
    if n == 0:
        return None
    p_o = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    p_e = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((p_o - p_e) / (1 - p_e), 3) if p_e < 1 else 1.0


def score_labeller_agreement(items: list) -> dict:
    """Agreement between labeler_1 and labeler_2 on the golden set, before
    reconciliation: per-rule % agreement + Cohen's kappa, and overall_score."""
    l1 = [it["human_labels"]["labeler_1"] for it in items]
    l2 = [it["human_labels"]["labeler_2"] for it in items]
    n = len(items)
    per_rule = {}
    for band, field in ALL_RULE_PATHS:
        a = [x[band][field] for x in l1]
        b = [x[band][field] for x in l2]
        per_rule[f"{band}.{field}"] = {**_count_pct(sum(x == y for x, y in zip(a, b)), n), "kappa": cohen_kappa(a, b)}
    s1 = [x["overall_score"] for x in l1]
    s2 = [x["overall_score"] for x in l2]
    all_12_agree = sum(all(x[b][f] == y[b][f] for b, f in ALL_RULE_PATHS) for x, y in zip(l1, l2))
    return {
        "n_items": n,
        "per_rule_agreement": per_rule,
        "all_12_rules_agree": _count_pct(all_12_agree, n),
        "overall_score_exact": {**_count_pct(sum(x == y for x, y in zip(s1, s2)), n), "kappa": cohen_kappa(s1, s2)},
        "overall_score_within_1": _count_pct(sum(abs(x - y) <= 1 for x, y in zip(s1, s2)), n),
    }


def score_judge_validation(rows: list) -> dict:
    """Judge vs the human reconciled_label: per-rule agreement (count, %,
    kappa) and overall_score match."""
    n = len(rows)
    ok = [r for r in rows if "error" not in r["judge_verdict"]]
    n_scored = len(ok)

    per_rule = {}
    for band, field in ALL_RULE_PATHS:
        j = [r["judge_verdict"][band][field] for r in ok]
        h = [r["reconciled_label"][band][field] for r in ok]
        per_rule[f"{band}.{field}"] = {**_count_pct(sum(x == y for x, y in zip(j, h)), n_scored), "kappa": cohen_kappa(j, h)}
    js = [r["judge_verdict"]["overall_score"] for r in ok]
    hs = [r["reconciled_label"]["overall_score"] for r in ok]

    return {
        "n_items": n,
        "n_errors": n - n_scored,
        "n_scored": n_scored,
        "error_reasons": [r["judge_verdict"]["error"] for r in rows if "error" in r["judge_verdict"]][:10],
        "per_rule_agreement": per_rule,
        "score_exact_match": {**_count_pct(sum(x == y for x, y in zip(js, hs)), n_scored), "kappa": cohen_kappa(js, hs)},
        "score_within_1": _count_pct(sum(abs(x - y) <= 1 for x, y in zip(js, hs)), n_scored),
        "judge_latency_and_cost": _meta_stats([r["judge_verdict"] for r in rows]),
    }


def score_system_run(rows: list) -> dict:
    """For rows produced by running the system + judge on briefs (no human
    label for the system's emails — this is the judge-measured system score)."""
    n = len(rows)
    scored = [r for r in rows if "error" not in r.get("judge_verdict", {}) and "error" not in r.get("system_output", {})]
    n_scored = len(scored)

    rule_pass = {}
    for band, field in ALL_RULE_PATHS:
        rule_pass[f"{band}.{field}"] = _count_pct(sum(1 for r in scored if r["judge_verdict"][band][field]), n_scored)

    scores = [r["judge_verdict"]["overall_score"] for r in scored]
    return {
        "n_items": n,
        "n_errors": n - n_scored,
        "n_scored": n_scored,
        "average_overall_score": round(sum(scores) / len(scores), 3) if scores else None,
        "score_distribution": {str(k): _count_pct(scores.count(k), n_scored) for k in range(1, 6)},
        "scored_4_or_5": _count_pct(sum(1 for s in scores if s >= 4), n_scored),
        "per_rule_pass_rate": rule_pass,
        "system_latency_and_cost": _meta_stats([r.get("system_output", {}) for r in rows]),
        "judge_latency_and_cost": _meta_stats([r.get("judge_verdict", {}) for r in rows]),
    }


def score_judge_bias(rows: list) -> dict:
    """Summary of the verbosity (padding) and position (order swap) probes."""
    v = [r["verbosity_bias"] for r in rows if "verbosity_bias" in r and "error" not in r["verbosity_bias"]]
    p = [r["position_bias"] for r in rows if "position_bias" in r and "error" not in r["position_bias"]]
    nv, np_ = len(v), len(p)
    return {
        "verbosity": {
            "n_pairs": nv,
            "n_errors": sum(1 for r in rows if "error" in r.get("verbosity_bias", {})),
            "score_went_up": _count_pct(sum(x["score_delta"] > 0 for x in v), nv),
            "score_unchanged": _count_pct(sum(x["score_delta"] == 0 for x in v), nv),
            "score_went_down": _count_pct(sum(x["score_delta"] < 0 for x in v), nv),
            "concise_flagged_on_padded": _count_pct(sum(x["concise_flagged_on_padded"] for x in v), nv),
            "avg_score_delta": round(sum(x["score_delta"] for x in v) / nv, 3) if nv else None,
        },
        "position": {
            "n_pairs": np_,
            "n_errors": sum(1 for r in rows if "error" in r.get("position_bias", {})),
            "verdict_flipped_after_swap": _count_pct(sum(x["verdict_flipped"] for x in p), np_),
            "picked_first_both_times": _count_pct(sum(x["picked_first_both_times"] for x in p), np_),
            "picked_second_both_times": _count_pct(sum(x["picked_second_both_times"] for x in p), np_),
            "agrees_with_humans_both_orders": _count_pct(sum(x["agrees_with_humans_both_orders"] for x in p), np_),
        },
        "judge_latency_and_cost": _meta_stats(
            [r.get("verbosity_bias", {}) for r in rows] + [r.get("position_bias", {}) for r in rows]),
    }

"""
harness/scorer.py — turns a list of per-item result rows into the summary
numbers required by the slides: "report as counts and percentages, never
only one summary number." Also aggregates latency/token usage from the
"_meta" block llm_client.call_json now attaches to every successful call —
the slides explicitly require "cost and latency per judged item".
"""
from harness.schema import ALL_RULE_PATHS
from harness.rule_checks import judge_missed_placeholder

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
        "models": sorted({m["model"] for m in metas if m.get("model")}),
        "avg_latency_s": sum(latencies) / len(latencies) if latencies else None,
        "max_latency_s": max(latencies) if latencies else None,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "estimated_cost_usd": est_cost_usd,
        "estimated_cost_per_1k_items_usd": (est_cost_usd / len(metas) * 1000) if est_cost_usd is not None and metas else None,
    }


def _rule_check_stats(rows: list) -> dict:
    """Counts from the deterministic checks in harness/rule_checks.py, and
    how many of those items the judge still passed on the matching rule."""
    checked = [r for r in rows if isinstance(r.get("rule_checks"), dict)]
    flagged = [r for r in checked if r["rule_checks"].get("placeholders")]
    missed = [r for r in flagged if judge_missed_placeholder(r["rule_checks"], r.get("judge_verdict", {}))]
    return {
        "n_checked": len(checked),
        "n_with_placeholders": len(flagged),
        "pct_with_placeholders": len(flagged) / len(checked) if checked else None,
        "n_placeholder_but_judge_passed_correct_names": len(missed),
        "placeholder_item_ids": [r["id"] for r in flagged],
        "judge_missed_placeholder_ids": [r["id"] for r in missed],
    }


def _score_by_tag(scored_rows: list) -> dict:
    """Average score and count of sub-5 items per brief `tests` tag (e.g.
    negative_constraint, many_key_points), so the report can say WHICH kind
    of brief the system fails on, not just one overall number."""
    by_tag = {}
    for r in scored_rows:
        for tag in r.get("tests") or []:
            by_tag.setdefault(tag, []).append(r["judge_verdict"]["overall_score"])
    return {
        tag: {"n": len(s), "average_score": sum(s) / len(s), "n_below_5": sum(1 for x in s if x < 5)}
        for tag, s in sorted(by_tag.items())
    }


def _cohens_kappa(a: list, b: list):
    """Cohen's kappa for two equal-length label lists. None when chance
    agreement is 1 (both labellers used a single identical value), where
    kappa is undefined."""
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    values = set(a) | set(b)
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in values)
    return None if pe == 1 else (po - pe) / (1 - pe)


def score_label_agreement(items: list) -> dict:
    """Inter-labeller agreement on the golden set: labeler_1 vs labeler_2,
    computed on the raw labels BEFORE reconciliation (labelling guide,
    step 2). Percent agreement is the headline; kappa is reported beside it
    but is misleading on rules where nearly every label is the same value."""
    n = len(items)
    l1 = [it["human_labels"]["labeler_1"] for it in items]
    l2 = [it["human_labels"]["labeler_2"] for it in items]
    per_rule = {}
    for band, field in ALL_RULE_PATHS:
        a = [x[band][field] for x in l1]
        b = [x[band][field] for x in l2]
        kappa = _cohens_kappa(a, b)
        per_rule[f"{band}.{field}"] = {
            "agree": sum(x == y for x, y in zip(a, b)),
            "pct_agreement": sum(x == y for x, y in zip(a, b)) / n if n else None,
            "cohens_kappa": round(kappa, 3) if kappa is not None else None,
        }
    s1 = [x["overall_score"] for x in l1]
    s2 = [x["overall_score"] for x in l2]
    rule_pairs = [(x[b][f], y[b][f]) for x, y in zip(l1, l2) for b, f in ALL_RULE_PATHS]
    kappa_score = _cohens_kappa(s1, s2)
    return {
        "n_items": n,
        "n_dropped": 0,
        "dropped_reason": "none dropped: every item has both labels and a reconciled_label",
        "all_rule_labels_agree": sum(x == y for x, y in rule_pairs),
        "all_rule_labels_total": len(rule_pairs),
        "pct_all_rule_labels_agree": sum(x == y for x, y in rule_pairs) / len(rule_pairs) if rule_pairs else None,
        "n_items_with_any_disagreement": sum(
            1 for x, y in zip(l1, l2)
            if x["overall_score"] != y["overall_score"] or any(x[b][f] != y[b][f] for b, f in ALL_RULE_PATHS)
        ),
        "overall_score_exact": sum(x == y for x, y in zip(s1, s2)),
        "overall_score_within_1": sum(abs(x - y) <= 1 for x, y in zip(s1, s2)),
        "overall_score_cohens_kappa": round(kappa_score, 3) if kappa_score is not None else None,
        "per_rule": per_rule,
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
        "rule_checks": _rule_check_stats(rows),
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
        "score_distribution": {s: scores.count(s) for s in range(1, 6)},
        "by_brief_tag": _score_by_tag(scored),
        "rule_checks": _rule_check_stats(rows),
        "system_latency_and_cost": _meta_stats([r.get("system_output", {}) for r in rows]),
        "judge_latency_and_cost": _meta_stats([r.get("judge_verdict", {}) for r in rows]),
    }

"""
harness/judge.py — the LLM judge. Takes a (brief, email) pair, returns a
structured verdict against the 12-rule style guide.

Also implements the two bias probes the slides require in the judge's
reliability report ("What to measure" -> Judge):
  - verbosity_bias_check: pad a candidate email with content-free filler
    and see if the score goes up without the content improving.
  - position_bias_check: the slides' "swap the order of two answers" test.
    A second, pairwise judge (prompts/judge_pairwise_v1.txt) is shown two
    emails for the SAME brief and must pick the better one. We ask twice,
    A/B then B/A. A consistent judge picks the same email both times; if the
    verdict flips, the judge followed the position, not the content.
"""
import json
from pathlib import Path

from harness.llm_client import call_json
from harness.schema import validate_judge_verdict, validate_pairwise_verdict, RULE_FIELDS, ALL_RULE_PATHS

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"

_FILLER_SENTENCES = [
    "Please let me know if you have any questions at all, any time.",
    "I really appreciate your patience and understanding on this matter.",
    "Thank you again for your continued attention to this.",
    "As always, feel free to reach out with anything further.",
]


def load_judge_prompt(version: str) -> str:
    path = PROMPTS_DIR / f"judge_prompt_{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file at {path}")
    return path.read_text(encoding="utf-8")


def _fill_prompt(template: str, brief: dict, email: str) -> str:
    brief_json = json.dumps(brief, ensure_ascii=False, indent=2)
    return template.replace("<<BRIEF_JSON>>", brief_json).replace("<<EMAIL_TEXT>>", email)


def judge_email(brief: dict, email: str, prompt_version: str = "v1") -> dict:
    """Runs the judge on one (brief, email) pair. Returns the verdict dict
    (with a "_meta" latency/usage key on success), or {"error": ...} if the
    call/parsing failed or the shape was invalid. Never raises."""
    template = load_judge_prompt(prompt_version)
    filled = _fill_prompt(template, brief, email)
    verdict = call_json(filled)
    if "error" in verdict:
        return verdict
    try:
        validate_judge_verdict(verdict)
    except ValueError as e:
        return {"error": str(e), "raw_output": verdict}
    return verdict


def compare_to_reconciled(verdict: dict, reconciled: dict) -> dict:
    """Per-rule match + overall_score match, against a golden-set reconciled_label."""
    if "error" in verdict:
        return {"error": verdict["error"]}
    rule_matches = {
        f"{band}.{field}": verdict[band][field] == reconciled[band][field]
        for band, field in ALL_RULE_PATHS
    }
    return {
        "rule_matches": rule_matches,
        "score_exact": verdict.get("overall_score") == reconciled.get("overall_score"),
        "score_within_1": abs(verdict.get("overall_score", 0) - reconciled.get("overall_score", 0)) <= 1,
    }


def pad_email(email: str) -> str:
    """Adds content-free filler sentences to the end of the email body,
    just before the sign-off block, without adding any new facts or
    addressing any new key point. Used for the verbosity-bias probe."""
    lines = email.rstrip().split("\n")
    filler = "\n\n" + " ".join(_FILLER_SENTENCES)
    # Insert filler before the last two lines (assumed sign-off + name) if
    # there are enough lines to guess that shape; otherwise just append.
    if len(lines) >= 3:
        body = "\n".join(lines[:-2])
        tail = "\n".join(lines[-2:])
        return body + filler + "\n\n" + tail
    return email.rstrip() + filler


def verbosity_bias_check(brief: dict, email: str, prompt_version: str = "v1") -> dict:
    """Judges the original email, then a padded version of the SAME email,
    and reports whether the score/verdict changed. A well-calibrated judge
    should NOT reward the padded version — the prompt explicitly says not
    to reward length."""
    original = judge_email(brief, email, prompt_version)
    padded_text = pad_email(email)
    padded = judge_email(brief, padded_text, prompt_version)
    if "error" in original or "error" in padded:
        return {"error": original.get("error") or padded.get("error")}
    return {
        "original_score": original.get("overall_score"),
        "padded_score": padded.get("overall_score"),
        "score_delta": padded.get("overall_score", 0) - original.get("overall_score", 0),
        "score_increased_from_padding": padded.get("overall_score", 0) > original.get("overall_score", 0),
        "concise_flagged_on_padded": not padded["form"]["concise"],
        "original_verdict": {k: v for k, v in original.items() if k in RULE_FIELDS},
        "padded_verdict": {k: v for k, v in padded.items() if k in RULE_FIELDS},
        "_meta": [original.get("_meta"), padded.get("_meta")],
    }


def pairwise_judge(brief: dict, email_a: str, email_b: str, prompt_version: str = "v1") -> dict:
    """Asks the pairwise judge which of two emails is better. Returns
    {"winner": "A"|"B", "reason": ..., "_meta": ...} or {"error": ...}."""
    template = (PROMPTS_DIR / f"judge_pairwise_{prompt_version}.txt").read_text(encoding="utf-8")
    filled = (template.replace("<<BRIEF_JSON>>", json.dumps(brief, ensure_ascii=False, indent=2))
                      .replace("<<EMAIL_A>>", email_a)
                      .replace("<<EMAIL_B>>", email_b))
    verdict = call_json(filled)
    if "error" in verdict:
        return verdict
    try:
        validate_pairwise_verdict(verdict)
    except ValueError as e:
        return {"error": str(e), "raw_output": verdict}
    return verdict


def position_bias_check(brief: dict, better: str, worse: str, prompt_version: str = "v1") -> dict:
    """Shows the pair in both orders. `better` is the email the humans scored
    higher. Reports whether the verdict flipped with the order, whether the
    judge picked the first-shown email, and whether it agreed with the humans."""
    first = pairwise_judge(brief, better, worse, prompt_version)   # better shown as A
    second = pairwise_judge(brief, worse, better, prompt_version)  # better shown as B
    if "error" in first or "error" in second:
        return {"error": first.get("error") or second.get("error")}
    picked_better_1 = first["winner"] == "A"
    picked_better_2 = second["winner"] == "B"
    return {
        "order_1_winner": first["winner"],
        "order_2_winner": second["winner"],
        "verdict_flipped": picked_better_1 != picked_better_2,
        "picked_first_both_times": first["winner"] == "A" and second["winner"] == "A",
        "picked_second_both_times": first["winner"] == "B" and second["winner"] == "B",
        "agrees_with_humans_both_orders": picked_better_1 and picked_better_2,
        "reason_order_1": first.get("reason"),
        "reason_order_2": second.get("reason"),
        "_meta": [first.get("_meta"), second.get("_meta")],
    }

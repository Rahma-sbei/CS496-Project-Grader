"""
harness/judge.py — the LLM judge. Takes a (brief, email) pair, returns a
structured verdict against the 12-rule style guide.

Also implements the two bias probes the slides require in the judge's
reliability report ("What to measure" -> Judge):
  - verbosity_bias_check: pad a candidate email with content-free filler
    and see if the score goes up without the content improving.
  - order_bias_check: this task grades ONE email against a rubric — it is
    not a pairwise "pick the better answer" comparison, so there is no
    literal "swap answer order" to test. As the closest faithful analogue,
    we swap the order the BRIEF and CANDIDATE EMAIL blocks appear in the
    prompt and check whether the verdict changes. Document this adaptation
    in your report — it is not a drop-in substitute for true position bias,
    which only applies to comparison-style judges.
"""
import json
from pathlib import Path

from harness.llm_client import call_json
from harness.schema import validate_judge_verdict, RULE_FIELDS, ALL_RULE_PATHS

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


def _fill_prompt(template: str, brief: dict, email: str, swap_order: bool = False) -> str:
    brief_json = json.dumps(brief, ensure_ascii=False, indent=2)
    if not swap_order:
        filled = template.replace("<<BRIEF_JSON>>", brief_json)
        filled = filled.replace("<<EMAIL_TEXT>>", email)
        return filled
    # Order-bias probe: physically swap which block appears first in the
    # rendered prompt by swapping the two placeholder markers' positions.
    marker_brief = "\n\nBRIEF:\n" + brief_json
    marker_email = "\n\nCANDIDATE EMAIL:\n" + email
    filled = template.replace("\n\nBRIEF:\n<<BRIEF_JSON>>", "\x00BRIEF\x00")
    filled = filled.replace("\n\nCANDIDATE EMAIL:\n<<EMAIL_TEXT>>", "\x00EMAIL\x00")
    # Re-insert in reverse order of first appearance
    filled = filled.replace("\x00BRIEF\x00\x00EMAIL\x00", marker_email + marker_brief, 1)
    filled = filled.replace("\x00EMAIL\x00\x00BRIEF\x00", marker_brief + marker_email, 1)
    # Fallback if markers weren't adjacent (template changed): just do the plain fill
    if "\x00" in filled:
        filled = template.replace("<<BRIEF_JSON>>", brief_json).replace("<<EMAIL_TEXT>>", email)
    return filled


def judge_email(brief: dict, email: str, prompt_version: str = "v1", swap_order: bool = False) -> dict:
    """Runs the judge on one (brief, email) pair. Returns the verdict dict
    (with a "_meta" latency/usage key on success), or {"error": ...} if the
    call/parsing failed or the shape was invalid. Never raises."""
    template = load_judge_prompt(prompt_version)
    filled = _fill_prompt(template, brief, email, swap_order=swap_order)
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


def verbosity_bias_check(brief: dict, email: str, prompt_version: str = "v1", original: dict = None) -> dict:
    """Judges the original email, then a padded version of the SAME email,
    and reports whether the score/verdict changed. A well-calibrated judge
    should NOT reward the padded version — the prompt explicitly says not
    to reward length. Pass `original` (an existing normal-order verdict for
    this pair) to reuse it instead of paying for the same call again."""
    if original is None:
        original = judge_email(brief, email, prompt_version)
    padded_text = pad_email(email)
    padded = judge_email(brief, padded_text, prompt_version)
    if "error" in original or "error" in padded:
        return {"error": original.get("error") or padded.get("error")}
    return {
        "original_score": original.get("overall_score"),
        "padded_score": padded.get("overall_score"),
        "score_increased_from_padding": padded.get("overall_score", 0) > original.get("overall_score", 0),
        "original_verdict": {k: v for k, v in original.items() if k in RULE_FIELDS},
        "padded_verdict": {k: v for k, v in padded.items() if k in RULE_FIELDS},
    }


def order_bias_check(brief: dict, email: str, prompt_version: str = "v1", normal: dict = None) -> dict:
    """Judges the same (brief, email) pair with the BRIEF/EMAIL blocks in
    normal order and then swapped, and reports whether the verdict changed.
    See module docstring: this is an adaptation of "position bias" for a
    single-answer (not pairwise) judge. Pass `normal` to reuse an existing
    normal-order verdict (the same call verbosity_bias_check makes)."""
    if normal is None:
        normal = judge_email(brief, email, prompt_version, swap_order=False)
    swapped = judge_email(brief, email, prompt_version, swap_order=True)
    if "error" in normal or "error" in swapped:
        return {"error": normal.get("error") or swapped.get("error")}
    return {
        "normal_score": normal.get("overall_score"),
        "swapped_score": swapped.get("overall_score"),
        "score_changed": normal.get("overall_score") != swapped.get("overall_score"),
        "any_rule_changed": any(
            normal[band][field] != swapped[band][field] for band, field in ALL_RULE_PATHS
        ),
    }

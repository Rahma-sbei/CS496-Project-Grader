"""
harness/rule_checks.py — deterministic (non-LLM) checks that run next to the
judge. They do not change the judge's verdict; they are reported as a
separate column so every item where a rule check fires but the judge still
passed the matching rule is a *measured* judge miss.

Why this exists: system_prompt_v1 run 1 (see CHANGELOG.md, AUDIT) produced
8/50 emails with unfilled template placeholders ("Dear [Client Name],",
"[Your Name]") and judge_prompt_v3 scored all 8 as 5 with
correct_names=true. A regex catches this for free and cannot be talked out
of it by a polished-looking email.
"""
import re

# Words that mark a bracketed span as a template slot rather than normal
# text. Keeps "[attached]" or "[sic]" style brackets from being flagged.
_SLOT_WORDS = (
    r"name|title|company|organi[sz]ation|recipient|client|customer|sender|"
    r"date|time|day|number|amount|phone|email|address|position|role|team|"
    r"department|signature|insert|your|their|his|her|x{2,}"
)

_PLACEHOLDER_PATTERNS = [
    # [Client Name], [Your Name], [Date] — but not markdown links "[text](url)"
    re.compile(r"\[[^\[\]\n]{1,40}\](?!\()"),
    # {{name}}, {name}, {client_name}
    re.compile(r"\{\{?\s*[A-Za-z_][\w .-]{0,38}\}?\}"),
    # <Name>, <Client Name> — excludes email addresses like <a@b.com>
    re.compile(r"<[A-Za-z][A-Za-z _-]{0,38}>"),
    # XXX / xxxx fillers
    re.compile(r"\b[Xx]{3,}\b"),
]

_SLOT_RE = re.compile(_SLOT_WORDS, re.IGNORECASE)


def find_placeholders(email: str) -> list:
    """Returns the unfilled template placeholders found in `email`, in order
    of appearance, without duplicates. Empty list if none."""
    if not isinstance(email, str):
        return []
    found = []
    for pattern in _PLACEHOLDER_PATTERNS:
        for m in pattern.finditer(email):
            text = m.group(0)
            # Bracket/brace/angle spans only count if they look like a slot.
            if text[0] in "[{<" and not _SLOT_RE.search(text):
                continue
            found.append((m.start(), text))
    seen, ordered = set(), []
    for _, text in sorted(found):
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def run_rule_checks(email: str) -> dict:
    """All deterministic checks for one email. Add new checks here as keys."""
    return {"placeholders": find_placeholders(email)}


def judge_missed_placeholder(checks: dict, verdict: dict) -> bool:
    """True if the regex found a placeholder but the judge still passed
    correct_names — i.e. a judge miss we can count without a human."""
    if not checks.get("placeholders") or "error" in verdict:
        return False
    return bool(verdict.get("content", {}).get("correct_names"))

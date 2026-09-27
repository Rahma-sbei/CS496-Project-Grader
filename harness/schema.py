"""
harness/schema.py — the fixed structured-output contracts (objective #6 on
the slides: "make the model answer in a fixed schema so the harness can read
it"). Both system.py and judge.py validate their LLM output against these
before the harness trusts a result.
"""

RULE_FIELDS = {
    "structure": ["greeting", "body", "sign_off"],
    "tone": ["professional_register", "no_slang", "formality_matches_relationship"],
    "content": ["no_invented_facts", "addresses_all_points", "correct_names"],
    "form": ["grammatical", "concise", "well_paragraphed"],
}
ALL_RULE_PATHS = [(band, field) for band, fields in RULE_FIELDS.items() for field in fields]


def validate_judge_verdict(verdict: dict) -> None:
    """Raises ValueError if the judge's JSON doesn't match the required shape.

    Defensive: llm_client.call_json now guarantees a dict is returned (or an
    {"error": ...} dict), but this function no longer trusts that blindly —
    a non-dict here is a bug, not a silent crash.
    """
    if not isinstance(verdict, dict):
        raise ValueError(f"Judge output is not a JSON object (got {type(verdict).__name__})")
    for band, fields in RULE_FIELDS.items():
        if band not in verdict or not isinstance(verdict[band], dict):
            raise ValueError(f"Judge output missing object for band '{band}'")
        for field in fields:
            if field not in verdict[band]:
                raise ValueError(f"Judge output missing '{band}.{field}'")
            if not isinstance(verdict[band][field], bool):
                raise ValueError(f"'{band}.{field}' is not a boolean")
    if "overall_score" not in verdict or not isinstance(verdict["overall_score"], (int, float)):
        raise ValueError("Judge output missing numeric 'overall_score'")


def validate_system_output(output: dict) -> None:
    """Raises ValueError if the system's JSON doesn't match the required shape."""
    if not isinstance(output, dict):
        raise ValueError(f"System output is not a JSON object (got {type(output).__name__})")
    if "email" not in output or not isinstance(output["email"], str) or not output["email"].strip():
        raise ValueError("System output missing non-empty 'email' string")
    if "subject" not in output or not isinstance(output["subject"], str):
        raise ValueError("System output missing 'subject' string")

"""
harness/system.py — the email-writing LLM. This is the system under test.
Takes a brief, returns {"subject": ..., "email": ...}.

Uses llm_client_sys (a separate client/model from the judge's llm_client) so
the system is never graded by itself or a model in its own family — see
llm_client_sys.py's docstring and CHANGELOG.md for why this split exists.
"""
import json
from pathlib import Path

from harness.llm_client_sys import call_json_sys
from harness.schema import validate_system_output

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"


def load_system_prompt(version: str) -> str:
    path = PROMPTS_DIR / f"system_prompt_{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file at {path}")
    return path.read_text(encoding="utf-8")


def write_email(brief: dict, prompt_version: str = "v1") -> dict:
    """Runs the system on one brief. Returns {"subject", "email", "_meta"} or
    {"error": ...} if the call/parsing failed or the shape was invalid.
    Never raises."""
    template = load_system_prompt(prompt_version)
    filled = template.replace("<<BRIEF_JSON>>", json.dumps(brief, ensure_ascii=False, indent=2))
    output = call_json_sys(filled)
    if "error" in output:
        return output
    try:
        validate_system_output(output)
    except ValueError as e:
        return {"error": str(e), "raw_output": output}
    return output

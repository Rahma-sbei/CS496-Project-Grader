"""
The LLM judge. One model call per item, forced structured output via a tool
call, validated against schema.py. Never modifies or coaches the generator -
it only scores what it's given.
"""
from pathlib import Path

from . import llm_client
from .schema import validate_judge_result, SchemaValidationError, CRITERIA

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

JUDGE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "requirement_fulfillment": {"type": "integer", "minimum": 0, "maximum": 2},
        "accuracy": {"type": "integer", "minimum": 0, "maximum": 2},
        "tone": {"type": "integer", "minimum": 0, "maximum": 2},
        "clarity": {"type": "integer", "minimum": 0, "maximum": 2},
        "conciseness": {"type": "integer", "minimum": 0, "maximum": 2},
        "total_score": {"type": "integer", "minimum": 0, "maximum": 10},
        "reason": {
            "type": "string",
            "description": "1-3 sentence concise explanation of the scores. No chain-of-thought, just the justification.",
        },
    },
    "required": CRITERIA + ["total_score", "reason"],
}


def load_prompt(version: str = "v1") -> str:
    path = PROMPTS_DIR / f"judge_{version}.txt"
    return path.read_text()


def build_user_message(item: dict, email: dict) -> str:
    required = "\n".join(f"- {r}" for r in item["required_information"])
    email_text = (
        f"Subject: {email['subject']}\n\n"
        f"{email['greeting']}\n\n"
        f"{email['body']}\n\n"
        f"{email['closing']}"
    )
    return (
        "## Scenario\n"
        f"Category: {item['category']}\n"
        f"Scenario: {item['scenario']}\n"
        f"Recipient: {item['recipient']}\n"
        f"Purpose: {item['purpose']}\n"
        f"Context: {item['context']}\n"
        f"Required information:\n{required}\n"
        f"Desired tone: {item['tone']}\n"
        f"Maximum desired length: {item['max_length']}\n\n"
        "## Email to evaluate\n"
        f"{email_text}\n"
    )


def evaluate_email(item: dict, email: dict, prompt_version: str = "v1", model: str = None) -> dict:
    """
    Returns {"scores": {...} | None, "error": str | None, "usage": {...}}.
    Retries once on schema validation failure (per spec: "retry once, then
    record the failure"), never raises.
    """
    system_prompt = load_prompt(prompt_version)
    user_message = build_user_message(item, email)

    attempts_left = 2  # one try + one retry
    last_error = None
    while attempts_left > 0:
        attempts_left -= 1
        try:
            result = llm_client.call_with_tool(
                system=system_prompt,
                user_message=user_message,
                tool_name="submit_scores",
                tool_description="Submit the rubric scores as structured fields.",
                tool_input_schema=JUDGE_TOOL_SCHEMA,
                model=model,
                max_tokens=500,
            )
            raw = llm_client.extract_tool_input(result, "submit_scores")
            judged = validate_judge_result(raw)
            return {
                "scores": judged.to_dict(),
                "error": None,
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost_usd": result.estimated_cost_usd,
                    "model": result.model,
                    "prompt_version": prompt_version,
                },
            }
        except SchemaValidationError as e:
            last_error = f"schema_validation_error: {e}"
            continue  # retry once
        except llm_client.LLMError as e:
            last_error = f"llm_error: {e}"
            break  # don't retry hard API errors, just record
        except Exception as e:
            last_error = f"unexpected_error: {e}"
            break

    return {"scores": None, "error": last_error, "usage": None}

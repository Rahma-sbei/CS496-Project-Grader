"""
The email generator. Deliberately simple: one model call per scenario,
no tools, no retrieval, no multi-step agent behavior - per the assignment
constraints. All the "intelligence" the project is graded on lives in the
judge and the evaluation harness, not here.
"""
from pathlib import Path

from . import llm_client
from .schema import validate_generated_email, SchemaValidationError

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

GENERATOR_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Email subject line"},
        "greeting": {"type": "string", "description": "Opening greeting line, e.g. 'Dear Professor Lee,'"},
        "body": {"type": "string", "description": "The full body of the email, excluding greeting/closing"},
        "closing": {"type": "string", "description": "Closing line + sign-off, e.g. 'Best regards,\\nAlex'"},
    },
    "required": ["subject", "greeting", "body", "closing"],
}


def load_prompt(version: str = "v1") -> str:
    path = PROMPTS_DIR / f"generator_{version}.txt"
    return path.read_text()


def build_user_message(item: dict) -> str:
    required = "\n".join(f"- {r}" for r in item["required_information"])
    return (
        f"Category: {item['category']}\n"
        f"Scenario: {item['scenario']}\n"
        f"Recipient: {item['recipient']}\n"
        f"Purpose: {item['purpose']}\n"
        f"Context: {item['context']}\n"
        f"Required information to include:\n{required}\n"
        f"Desired tone: {item['tone']}\n"
        f"Maximum desired length: {item['max_length']}\n"
    )


def generate_email(item: dict, prompt_version: str = "v1", model: str = None) -> dict:
    """
    Returns a dict: {"email": {...} | None, "error": str | None, "usage": {...}}
    Never raises - callers (the API and the harness) rely on this to keep
    going even when generation fails for a single item.
    """
    system_prompt = load_prompt(prompt_version)
    user_message = build_user_message(item)

    try:
        result = llm_client.call_with_tool(
            system=system_prompt,
            user_message=user_message,
            tool_name="write_email",
            tool_description="Submit the generated email as structured fields.",
            tool_input_schema=GENERATOR_TOOL_SCHEMA,
            model=model,
            max_tokens=800,
        )
        raw = llm_client.extract_tool_input(result, "write_email")
        email = validate_generated_email(raw)
        return {
            "email": email.to_dict(),
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
        return {"email": None, "error": f"schema_validation_error: {e}", "usage": None}
    except llm_client.LLMError as e:
        return {"email": None, "error": f"llm_error: {e}", "usage": None}
    except Exception as e:  # never let one item crash the whole harness
        return {"email": None, "error": f"unexpected_error: {e}", "usage": None}

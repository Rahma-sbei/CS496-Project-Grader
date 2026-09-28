"""
Schemas and validation for the two structured LLM outputs in this project:
the generated email, and the judge's rubric scores. Both the harness and the
backend API import this module so validation logic lives in exactly one
place.
"""
from dataclasses import dataclass
from typing import Optional


CRITERIA = ["requirement_fulfillment", "accuracy", "tone", "clarity", "conciseness"]
MAX_PER_CRITERION = 2


class SchemaValidationError(Exception):
    """Raised when an LLM response does not match the expected schema."""


@dataclass
class GeneratedEmail:
    subject: str
    greeting: str
    body: str
    closing: str

    def to_dict(self):
        return {
            "subject": self.subject,
            "greeting": self.greeting,
            "body": self.body,
            "closing": self.closing,
        }


@dataclass
class JudgeResult:
    requirement_fulfillment: int
    accuracy: int
    tone: int
    clarity: int
    conciseness: int
    total_score: int
    reason: str

    def to_dict(self):
        return {
            "requirement_fulfillment": self.requirement_fulfillment,
            "accuracy": self.accuracy,
            "tone": self.tone,
            "clarity": self.clarity,
            "conciseness": self.conciseness,
            "total_score": self.total_score,
            "reason": self.reason,
        }


def validate_generated_email(data: dict) -> GeneratedEmail:
    required_fields = ["subject", "greeting", "body", "closing"]
    missing = [f for f in required_fields if not data.get(f) or not str(data.get(f)).strip()]
    if missing:
        raise SchemaValidationError(f"Generated email missing/empty fields: {missing}")
    return GeneratedEmail(
        subject=str(data["subject"]).strip(),
        greeting=str(data["greeting"]).strip(),
        body=str(data["body"]).strip(),
        closing=str(data["closing"]).strip(),
    )


def validate_judge_result(data: dict) -> JudgeResult:
    missing = [c for c in CRITERIA if c not in data]
    if missing:
        raise SchemaValidationError(f"Judge response missing criteria: {missing}")
    if "reason" not in data or not str(data.get("reason", "")).strip():
        raise SchemaValidationError("Judge response missing 'reason'")

    scores = {}
    for c in CRITERIA:
        value = data[c]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaValidationError(f"Criterion '{c}' must be numeric, got {value!r}")
        value = int(value)
        if not (0 <= value <= MAX_PER_CRITERION):
            raise SchemaValidationError(
                f"Criterion '{c}' must be between 0 and {MAX_PER_CRITERION}, got {value}"
            )
        scores[c] = value

    computed_total = sum(scores.values())
    # Trust the computed total over whatever the model reported, but require
    # it to at least be present as a sanity check on the model's own output.
    if "total_score" not in data:
        raise SchemaValidationError("Judge response missing 'total_score'")

    return JudgeResult(
        **scores,
        total_score=computed_total,
        reason=str(data["reason"]).strip(),
    )

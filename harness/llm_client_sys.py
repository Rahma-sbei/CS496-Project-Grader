"""
harness/llm_client_sys.py — a SECOND client, for the system under test only.

Why this exists: system.py and judge.py were both calling the same
llm_client.call_json(), which defaults to the same GROQ_MODEL for both the
email-writer and the grader. That means the system was being graded by
itself (or a model in the same family/style), which is a documented bias
(self-preference) — a model tends to score its own outputs, or outputs
written in its own house style, more favorably than an independent grader
would. See CHANGELOG.md for the incident this addresses: system_prompt_v1
scored a flat 1.0 on every rule for every item, which is not a credible
result for a subjective 12-rule rubric and was the signal that prompted
this split.

This module is deliberately thin: it reuses _extract_json from llm_client
(same JSON-shape guarantees, same defensive parsing) rather than
duplicating that logic, so a fix to JSON parsing only has to happen once.
It only re-implements the client setup and the retry loop, pointed at a
SEPARATE model via a separate env var, so the system-under-test and the
judge can never silently collapse onto the same model again.

Set GROQ_MODEL_SYS to a different model than GROQ_MODEL (the judge's model,
in llm_client.py) — the defaults below are already different models so this
is safe even if nobody sets an env var.
"""
import os
import time
from openai import OpenAI

from harness.llm_client import _extract_json, _PLACEHOLDER_KEY

# Deliberately a different default model family/size than llm_client.py's
# GROQ_MODEL, so system and judge are never the same model unless someone
# explicitly overrides both env vars to match.
GROQ_MODEL_SYS = os.getenv("GROQ_MODEL_SYS", "qwen/qwen3.8-27b")

_api_key = os.getenv("GROQ_API_KEY", _PLACEHOLDER_KEY)

groq_client_sys = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=_api_key,
)


def call_json_sys(system_prompt: str, model: str = None, retries: int = 1) -> dict:
    """Same contract as llm_client.call_json: always returns a dict, either
    the parsed JSON object (+ "_meta" latency/usage) or {"error": ...}.
    Never raises. Uses GROQ_MODEL_SYS by default, not GROQ_MODEL."""
    if _api_key == _PLACEHOLDER_KEY or not _api_key:
        return {
            "error": (
                "GROQ_API_KEY is not set (still the placeholder value). "
                "Export it before running the harness, e.g.:\n"
                "  export GROQ_API_KEY=gsk_...   (macOS/Linux)\n"
                "  setx GROQ_API_KEY gsk_...     (Windows, new shell after)"
            )
        }

    last_error = None
    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = groq_client_sys.chat.completions.create(
                model=model or GROQ_MODEL_SYS,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Return only the JSON object described above."},
                ],
            )
            latency_s = time.perf_counter() - start
            raw = response.choices[0].message.content
            parsed = _extract_json(raw)  # raises ValueError on bad shape — same guarantees as the judge's client

            usage = getattr(response, "usage", None)
            parsed["_meta"] = {
                "latency_s": round(latency_s, 3),
                "attempt": attempt + 1,
                "model": model or GROQ_MODEL_SYS,
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
            }
            return parsed
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt < retries:
                time.sleep(1)
    return {"error": f"{type(last_error).__name__}: {last_error}"}

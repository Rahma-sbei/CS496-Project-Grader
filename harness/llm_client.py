"""
harness/llm_client.py — one shared Groq client + a small helper for making a
call that must return valid JSON. Both system.py and judge.py use this so
there's a single place to change the API setup.

FIXES (see CHANGELOG / postmortem for the incident this addresses):
  1. Fails fast with a clear message if GROQ_API_KEY is missing/placeholder,
     instead of silently sending 50 requests that all 401.
  2. `_extract_json` now guarantees a dict or raises — a bare `null`, a list,
     or any other non-object JSON no longer slips past this function as if
     it were a valid verdict/output. Previously this caused an uncaught
     TypeError deep in judge.py/system.py ("argument of type 'NoneType' is
     not iterable") that crashed the whole harness run and lost all
     already-computed rows.
  3. call_json now records latency and (when the API returns it) token
     usage under "_meta" on every successful result, and always includes
     the raw exception text in "error" so failures are debuggable from the
     console instead of showing up as a bare "ERROR".
"""
import os
import json
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
_PLACEHOLDER_KEY = "your_groq_api_key_here"

_api_key = os.getenv("GROQ_API_KEY", _PLACEHOLDER_KEY)

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=_api_key,
)


def _extract_json(text: str) -> dict:
    """Parses the model's raw text into a JSON object.

    Raises ValueError (caught by call_json's try/except, turned into a
    normal {"error": ...} result) if the text isn't valid JSON, OR if it
    parses to something other than a JSON object. A bare `null`, `[1,2,3]`,
    `"some string"`, or `5` are all technically valid JSON but are not a
    usable verdict/output — callers downstream assume a dict.
    """
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    if not text:
        raise ValueError("Model returned an empty response")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Expected a JSON object, got {type(parsed).__name__}: {parsed!r}"
        )
    return parsed


def call_json(system_prompt: str, model: str = None, retries: int = 1) -> dict:
    """Calls the LLM with a fully-filled prompt and returns parsed JSON.

    Always returns a dict. On success the dict is the model's JSON object
    plus a "_meta" key with latency_s and (if available) token usage. On
    failure — auth error, network error, malformed JSON, non-object JSON —
    returns {"error": "<readable reason>"} after `retries` extra attempts.
    Never raises.
    """
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
            response = groq_client.chat.completions.create(
                model=model or GROQ_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Return only the JSON object described above."},
                ],
            )
            latency_s = time.perf_counter() - start
            raw = response.choices[0].message.content
            parsed = _extract_json(raw)  # raises ValueError on bad shape

            usage = getattr(response, "usage", None)
            parsed["_meta"] = {
                "latency_s": round(latency_s, 3),
                "attempt": attempt + 1,
                "model": model or GROQ_MODEL,
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
            }
            return parsed
        except Exception as e:  # noqa: BLE001 — anything (network, auth, JSON, shape) lands here
            last_error = e
            if attempt < retries:
                time.sleep(1)
    return {"error": f"{type(last_error).__name__}: {last_error}"}

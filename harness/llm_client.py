"""
Thin wrapper around the OpenRouter API.

Uses OpenRouter's OpenAI-compatible API while preserving the same
interface used by generator.py and judge.py.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


PRICING_PER_MTOK = {
    "openrouter/free": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING = {"input": 0.0, "output": 0.0}


@dataclass
class LLMCallResult:
    content_blocks: list
    input_tokens: int
    output_tokens: int
    model: str
    latency_seconds: float
    estimated_cost_usd: float


class LLMError(Exception):
    pass


def _get_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        raise LLMError(
            "OPENROUTER_API_KEY is not set. "
            "Add your OpenRouter API key to .env."
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "The Grader - Email Quality Evaluation Harness",
        },
    )


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:

    pricing = PRICING_PER_MTOK.get(model, DEFAULT_PRICING)

    return (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
    )


def call_with_tool(
    system: str,
    user_message: str,
    tool_name: str,
    tool_description: str,
    tool_input_schema: dict,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    max_retries: int = 3,
) -> LLMCallResult:

    model = model or os.environ.get(
        "DEFAULT_MODEL",
        "openrouter/free",
    )

    client = _get_client()

    tools = [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": tool_input_schema,
            },
        }
    ]

    last_error = None

    for attempt in range(max_retries):
        try:
            start = time.time()

            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                tools=tools,
                tool_choice={
                    "type": "function",
                    "function": {
                        "name": tool_name,
                    },
                },
            )

            latency = time.time() - start

            input_tokens = (
                response.usage.prompt_tokens
                if response.usage
                else 0
            )

            output_tokens = (
                response.usage.completion_tokens
                if response.usage
                else 0
            )

            message = response.choices[0].message

            # Convert OpenAI/OpenRouter tool calls into the same
            # structure expected by extract_tool_input().
            content_blocks = []

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    import json

                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "name": tool_call.function.name,
                            "input": json.loads(
                                tool_call.function.arguments
                            ),
                        }
                    )

            cost = estimate_cost(
                model,
                input_tokens,
                output_tokens,
            )

            return LLMCallResult(
                content_blocks=content_blocks,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
                latency_seconds=latency,
                estimated_cost_usd=cost,
            )

        except Exception as e:
            last_error = e

            error_string = str(e).lower()

            if (
                "429" in error_string
                or "500" in error_string
                or "502" in error_string
                or "503" in error_string
                or "timeout" in error_string
            ):
                time.sleep(min(2**attempt, 8))
                continue

            raise LLMError(
                f"API error: {e}"
            ) from e

    raise LLMError(
        f"LLM call failed after {max_retries} attempts: {last_error}"
    )


def extract_tool_input(
    result: LLMCallResult,
    tool_name: str,
) -> dict:

    for block in result.content_blocks:

        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == tool_name
        ):
            return block["input"]

    raise LLMError(
        f"No tool_use block named '{tool_name}' found in response"
    )

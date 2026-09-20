"""Shared Gemini client and JSON generation helpers."""

import asyncio
import json
import random
from typing import Any

from google import genai
from google.genai import types

from core.config import FALLBACK_MODEL, GEMINI_API_KEY


client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key":
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        print(f"[GEMINI] Warning: Could not initialize Gemini client: {exc}")
else:
    print("[GEMINI] Warning: GEMINI_API_KEY is not configured. Agents requiring LLM will prompt for configuration.")



PERMANENT_ERROR_MARKERS = (
    "404",
    "not_found",
    "invalid model",
    "model is not found",
    "permission denied",
    "api key",
    "invalid_argument",
)

# Gemini returns these when a model is briefly saturated or rate
# limited. They are worth waiting out rather than failing the run.
OVERLOAD_MARKERS = (
    "503",
    "unavailable",
    "high demand",
    "overloaded",
    "429",
    "resource_exhausted",
    "rate limit",
)


def is_permanent_error(error: Exception) -> bool:
    text = str(error).lower()

    return any(
        marker in text
        for marker in PERMANENT_ERROR_MARKERS
    )


def is_overloaded(error: Exception) -> bool:
    text = str(error).lower()

    return any(marker in text for marker in OVERLOAD_MARKERS)


def is_quota_exhausted(error: Exception) -> bool:
    """Distinguish a spent daily quota from a momentary rate limit."""

    text = str(error).lower()

    return (
        "resource_exhausted" in text
        or "exceeded your current quota" in text
        or "free_tier" in text
    )


class QuotaExhaustedError(RuntimeError):
    """The API key has no quota left for this model."""


async def generate_json(
    model: str,
    prompt: str,
    system_instruction: str | None = None,
    tools: list[Any] | None = None,
    max_retries: int = 4,
    retry_delay: float = 1.0,
) -> dict[str, Any]:
    """Call Gemini and parse the response as a JSON object.

    Retries transient failures with exponential backoff and jitter.
    Permanent failures (bad model, bad key) are raised immediately. When
    the primary model stays saturated, the call falls back to
    GEMINI_FALLBACK_MODEL for one final attempt.
    """

    config_kwargs: dict[str, Any] = {}

    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    if tools:
        # Tool use and forced JSON mime types are mutually exclusive,
        # so grounded calls parse the JSON out of the text response.
        config_kwargs["tools"] = tools
    else:
        config_kwargs["response_mime_type"] = "application/json"

    config = types.GenerateContentConfig(**config_kwargs)

    async def call(target_model: str) -> dict[str, Any]:
        response = await client.aio.models.generate_content(
            model=target_model,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return parse_json_object(response.text)

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):

        try:
            return await call(model)

        except Exception as exc:
            last_error = exc

            if is_permanent_error(exc):
                raise

            if attempt >= max_retries:
                break

            # Saturation clears on its own, so back off harder for it
            # than for an ordinary transient error.
            base = retry_delay * (3 if is_overloaded(exc) else 1)

            delay = base * (2 ** attempt)

            delay += random.uniform(0, delay * 0.25)

            print(
                f"[GEMINI] {model} attempt {attempt + 1}/"
                f"{max_retries + 1} failed, retrying in "
                f"{delay:.1f}s: {str(exc)[:120]}"
            )

            await asyncio.sleep(delay)

    if (
        FALLBACK_MODEL
        and FALLBACK_MODEL != model
        and last_error
        and is_overloaded(last_error)
    ):
        print(
            f"[GEMINI] {model} still unavailable; falling back to "
            f"{FALLBACK_MODEL}."
        )

        for attempt in range(3):
            try:
                return await call(FALLBACK_MODEL)

            except Exception as exc:
                last_error = exc

                if is_permanent_error(exc) or attempt == 2:
                    break

                await asyncio.sleep(retry_delay * (2 ** attempt))

    if last_error and is_quota_exhausted(last_error):
        raise QuotaExhaustedError(
            f"The Gemini API key has no quota left for {model} "
            f"(and fallback {FALLBACK_MODEL}). This key is on the free "
            "tier, which allows only a few requests per day per model. "
            "Enable billing on the Google AI Studio project, or point "
            "GEMINI_MODEL at a model that still has quota."
        ) from last_error

    raise last_error or RuntimeError("Gemini call failed.")


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating markdown fences around it."""

    candidate = text.strip()

    if candidate.startswith("```"):
        candidate = candidate.split("```", 2)[1]

        if candidate.lower().startswith("json"):
            candidate = candidate[4:]

        candidate = candidate.strip()

    try:
        result = json.loads(candidate)

    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")

        if start == -1 or end <= start:
            raise RuntimeError("Gemini returned invalid JSON.")

        result = json.loads(candidate[start:end + 1])

    if not isinstance(result, dict):
        raise RuntimeError("Gemini returned a non-object JSON response.")

    return result


def clamp_score(value: Any, low: float = 0, high: float = 100) -> float:
    """Coerce a model-supplied score into the allowed range."""

    try:
        number = float(value)

    except (TypeError, ValueError):
        return low

    return round(max(low, min(high, number)), 2)

import json
import re
from typing import Any
from google import genai
from google.genai import types

from config import MODEL_NAME, call_gemini_resilient, validate_api_key

CHECKPOINT_KEYS = [
    "accurate_and_grounded",
    "beginner_friendly_language",
    "teaches_by_example",
    "no_unexplained_jargon",
    "covers_key_points",
    "coherent_teaching_flow",
]


def extract_json_from_response(raw_text: str) -> dict[str, Any]:
    """
    Extract and parse JSON object from model output defensively.
    Handles markdown code blocks and stray surrounding text.
    """
    cleaned = raw_text.strip()

    # Strip code block fences ```json ... ``` or ``` ... ```
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # If surrounded by text, find first '{' and last '}'
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object, got {type(parsed)}")

    return parsed


def validate_evaluation_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate that all 6 required checkpoints are present with 'pass' (bool)
    and 'reason' (str). Deterministically calculate 'overall_pass'.
    """
    validated: dict[str, Any] = {}

    for key in CHECKPOINT_KEYS:
        item = data.get(key)
        if not isinstance(item, dict):
            raise ValueError(f"Missing or invalid checkpoint object: '{key}'")

        pass_val = item.get("pass")
        if not isinstance(pass_val, bool):
            # Attempt to coerce string representations if model returned "true"/"false"
            if str(pass_val).strip().lower() == "true":
                pass_val = True
            elif str(pass_val).strip().lower() == "false":
                pass_val = False
            else:
                raise ValueError(f"Checkpoint '{key}' 'pass' field must be boolean, got: {pass_val}")

        reason_val = str(item.get("reason", "")).strip()
        if not reason_val:
            reason_val = "Passed all checks." if pass_val else "Failed quality criteria."

        validated[key] = {
            "pass": pass_val,
            "reason": reason_val,
        }

    # Deterministic overall pass: TRUE only if ALL 6 checkpoints pass
    validated["overall_pass"] = all(validated[k]["pass"] is True for k in CHECKPOINT_KEYS)

    return validated


def build_evaluator_prompt(topic: str, lesson: str) -> str:
    """Build the prompt instructing the model to strictly evaluate the lesson."""
    return f"""You are a strict curriculum evaluator grading an educational lesson against a quality rubric.

TOPIC: {topic}

LESSON CONTENT:
---
{lesson}
---

Evaluate this lesson strictly across the following 6 checkpoints. No partial credit is allowed — each checkpoint is strictly true (PASS) or false (FAIL).

CHECKPOINTS:
1. accurate_and_grounded: Is the content technically accurate, factual, and correct? Does it explain the mechanism properly without hallucinated claims or factual errors?
2. beginner_friendly_language: Is the language simple, direct, and accessible to a learner with zero background and non-English-medium education? Are sentences short and plain?
3. teaches_by_example: Does the lesson include at least one concrete, end-to-end worked example or relatable analogy illustrating the concept?
4. no_unexplained_jargon: Are all technical terms and acronyms either avoided or clearly defined in simple terms before/at first use? (FAIL if technical jargon is left unexplained).
5. covers_key_points: Does the lesson explicitly explain What it is, Why it matters, and How it works?
6. coherent_teaching_flow: Does the lesson have a clean narrative with a clear Beginning (introduction), Middle (explanation & example), and End (recap & learning takeaway)?

OUTPUT FORMAT REQUIREMENTS:
You MUST return ONLY a valid JSON object with the exact keys below. Do not include markdown commentary outside the JSON.

{{
  "accurate_and_grounded": {{"pass": true, "reason": "brief explanation..."}},
  "beginner_friendly_language": {{"pass": true, "reason": "brief explanation..."}},
  "teaches_by_example": {{"pass": true, "reason": "brief explanation..."}},
  "no_unexplained_jargon": {{"pass": true, "reason": "brief explanation..."}},
  "covers_key_points": {{"pass": true, "reason": "brief explanation..."}},
  "coherent_teaching_flow": {{"pass": true, "reason": "brief explanation..."}},
  "overall_pass": false
}}
"""


def evaluate_lesson(
    topic: str,
    lesson: str,
    client: Any = None,
) -> dict[str, Any]:
    """
    Evaluate a lesson against the 6 rubric checkpoints.
    Retries once on JSON parsing/schema validation failure.
    Returns validated dict with deterministic 'overall_pass'.
    """
    prompt = build_evaluator_prompt(topic, lesson)

    if client is None:
        api_key = validate_api_key()
        client = genai.Client(api_key=api_key)

    last_error = None

    # Allow 1 retry on malformed/unparseable JSON
    for attempt in range(2):
        try:
            raw_text = call_gemini_resilient(
                client=client,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            parsed = extract_json_from_response(raw_text)
            return validate_evaluation_dict(parsed)

        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Evaluator failed to produce valid JSON evaluation after 2 attempts: {last_error}")


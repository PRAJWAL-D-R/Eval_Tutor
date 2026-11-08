import os
import time
from typing import Any
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# API Key - support both GEMINI_API_KEY and GOOGLE_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")

# Model selection - default to gemini-3.5-flash-lite (fast & stable) with fallbacks
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash"]

# Retry cap
MAX_RETRIES = 2

# Storage & logging paths
DATA_DIR = "data"
RUNS_DIR = os.path.join(DATA_DIR, "runs")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")
LOGS_DIR = "logs"
REJECTION_LOG_FILE = os.path.join(LOGS_DIR, "rejection_log.json")
FINAL_LESSON_FILE = os.path.join(RUNS_DIR, "final_lesson.md")


def validate_api_key() -> str:
    """Ensure API key is configured, raising a clear error if missing."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY (or GOOGLE_API_KEY) "
            "in your .env file. "
            "Get a key at: https://aistudio.google.com/app/apikey"
        )
    return key


def call_gemini_resilient(
    client: Any,
    contents: str,
    config: Any = None,
) -> str:
    """
    Call Gemini with automatic exponential backoff on 503/429
    and automatic fallback to alternate models if a model is temporarily unavailable.
    """
    models_to_try = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    last_error = None

    for model in models_to_try:
        for attempt in range(3):
            try:
                kwargs: dict[str, Any] = {"model": model, "contents": contents}
                if config is not None:
                    kwargs["config"] = config

                response = client.models.generate_content(**kwargs)
                if response.text:
                    return response.text.strip()
                raise RuntimeError(f"Model '{model}' returned empty response text.")

            except Exception as e:
                err_msg = str(e)
                last_error = e

                # Check for transient server load errors
                is_transient = any(code in err_msg for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"))
                if is_transient:
                    wait_sec = 2 * (attempt + 1)
                    print(f"  [Notice] Model '{model}' high demand/rate-limited. Retrying in {wait_sec}s (attempt {attempt + 1}/3)...")
                    time.sleep(wait_sec)
                    continue
                else:
                    print(f"  [Notice] Model '{model}' unavailable ({err_msg[:80]}...). Trying next candidate model...")
                    break

    raise RuntimeError(f"All Gemini models ({models_to_try}) failed to generate content: {last_error}")

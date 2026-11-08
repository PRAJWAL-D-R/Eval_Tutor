import json
import os
from datetime import datetime
from typing import Any

from config import DATA_DIR, LOGS_DIR, MEMORY_FILE, REJECTION_LOG_FILE, RUNS_DIR

CHECKPOINT_INSTRUCTIONS = {
    "accurate_and_grounded": (
        "Note: Past lessons had technical accuracy issues. "
        "Ensure all factual claims and descriptions of mechanisms are strictly accurate and grounded."
    ),
    "beginner_friendly_language": (
        "Note: Past lessons have repeatedly failed on beginner-friendly language. "
        "Use shorter sentences, everyday words, and avoid complex or academic phrasing."
    ),
    "teaches_by_example": (
        "Note: Past lessons lacked clear practical illustration. "
        "Include a complete, concrete, step-by-step example or relatable analogy."
    ),
    "no_unexplained_jargon": (
        "Note: Past lessons contained unexplained jargon. "
        "Define every technical term in simple language before or immediately upon using it."
    ),
    "covers_key_points": (
        "Note: Past lessons missed core concepts. "
        "Make sure to explicitly explain what it is, why it matters, and how it works."
    ),
    "coherent_teaching_flow": (
        "Note: Past lessons suffered from disjointed flow. "
        "Ensure a clear beginning -> middle -> end narrative that a beginner can follow from start to finish."
    ),
}


def save_run(run_data: dict[str, Any]) -> str:
    """Save full run data to data/runs/<timestamp>.json."""
    os.makedirs(RUNS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = os.path.join(RUNS_DIR, f"run_{timestamp}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)
    return filepath


def append_rejection_log(entries: list[dict[str, Any]]) -> None:
    """Append structured failed attempt records to logs/rejection_log.json."""
    if not entries:
        return

    os.makedirs(LOGS_DIR, exist_ok=True)
    existing_entries: list[dict[str, Any]] = []

    if os.path.exists(REJECTION_LOG_FILE):
        try:
            with open(REJECTION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    loaded = json.loads(content)
                    if isinstance(loaded, list):
                        existing_entries = loaded
                    elif isinstance(loaded, dict):
                        existing_entries = [loaded]
        except Exception:
            existing_entries = []

    existing_entries.extend(entries)

    with open(REJECTION_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_entries, f, indent=2)


def load_memory() -> dict[str, Any]:
    """Load cross-run learned memory from data/memory.json."""
    if not os.path.exists(MEMORY_FILE):
        return {
            "checkpoint_failure_counts": {},
            "standing_instructions": [],
        }

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "checkpoint_failure_counts": {},
            "standing_instructions": [],
        }


def save_memory(data: dict[str, Any]) -> None:
    """Save cross-run learned memory to data/memory.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def update_memory_from_runs() -> dict[str, Any]:
    """
    Read all run files in data/runs/ and aggregate failures per checkpoint.
    If a checkpoint has failed in >1 past run, add a standing instruction
    to sharpen future prompts.
    """
    if not os.path.exists(RUNS_DIR):
        return load_memory()

    run_files = [f for f in os.listdir(RUNS_DIR) if f.endswith(".json")]
    failure_counts: dict[str, int] = {}

    for run_file in run_files:
        run_path = os.path.join(RUNS_DIR, run_file)
        try:
            with open(run_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            # Look through attempts in this run
            attempts = run_data.get("attempts", [])
            run_failed_checkpoints: set[str] = set()

            for attempt in attempts:
                result = attempt.get("result", {})
                for checkpoint in CHECKPOINT_INSTRUCTIONS.keys():
                    check = result.get(checkpoint)
                    if isinstance(check, dict) and check.get("pass") is False:
                        run_failed_checkpoints.add(checkpoint)

            for cp in run_failed_checkpoints:
                failure_counts[cp] = failure_counts.get(cp, 0) + 1

        except Exception:
            continue

    standing_instructions: list[str] = []
    for cp, count in failure_counts.items():
        # If failed in > 1 run, activate standing instruction
        if count > 1 and cp in CHECKPOINT_INSTRUCTIONS:
            standing_instructions.append(CHECKPOINT_INSTRUCTIONS[cp])

    memory_data = {
        "total_runs_analyzed": len(run_files),
        "checkpoint_failure_counts": failure_counts,
        "standing_instructions": standing_instructions,
        "last_updated": datetime.now().isoformat(),
    }

    save_memory(memory_data)
    return memory_data

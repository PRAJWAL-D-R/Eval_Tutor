import os
from datetime import datetime
from typing import Any

from config import FINAL_LESSON_FILE, MAX_RETRIES, REJECTION_LOG_FILE, RUNS_DIR
from evaluator import CHECKPOINT_KEYS, evaluate_lesson
from generator import generate_lesson
from memory import append_rejection_log, save_run, update_memory_from_runs


def run_pipeline(
    topic: str,
    generator_fn: Any = None,
    evaluator_fn: Any = None,
) -> dict[str, Any]:
    """
    Run the generate -> evaluate -> regenerate loop.
    Hard capped at MAX_RETRIES.
    Logs failed attempts to rejection_log.json.
    Saves full run to data/runs/<timestamp>.json and final lesson to data/runs/final_lesson.md.
    Updates cross-run memory.
    """
    gen_call = generator_fn or generate_lesson
    eval_call = evaluator_fn or evaluate_lesson

    attempt = 0
    feedback: list[str] | None = None
    history: list[dict[str, Any]] = []

    print(f"\n=======================================================")
    print(f"Starting Content Generation Pipeline")
    print(f"Topic: {topic}")
    print(f"Max retries allowed: {MAX_RETRIES}")
    print(f"=======================================================\n")

    while True:
        print(f"--- [Attempt {attempt + 1} of {MAX_RETRIES + 1}] Generating lesson ---")
        lesson = gen_call(topic=topic, feedback=feedback)

        print(f"--- [Attempt {attempt + 1}] Evaluating lesson against 6 rubric checkpoints ---")
        eval_result = eval_call(topic=topic, lesson=lesson)

        # Record this attempt
        history.append({
            "attempt": attempt,
            "lesson": lesson,
            "result": eval_result,
        })

        # Check if overall pass
        is_passed = eval_result.get("overall_pass", False)

        # Print checkpoint status summary
        for cp in CHECKPOINT_KEYS:
            status_symbol = "✓ PASS" if eval_result[cp]["pass"] else "✗ FAIL"
            print(f"  [{status_symbol}] {cp}: {eval_result[cp]['reason']}")

        if is_passed:
            print(f"\n>>> Attempt {attempt + 1} PASSED all 6 quality checks! <<<\n")
            break

        if attempt >= MAX_RETRIES:
            print(f"\n>>> Attempt {attempt + 1} failed and retry limit reached ({MAX_RETRIES} retries). Shipping final attempt with known issues. <<<\n")
            break

        # Collect feedback for next attempt
        failed_reasons: list[str] = []
        for cp in CHECKPOINT_KEYS:
            if not eval_result[cp]["pass"]:
                failed_reasons.append(f"{cp}: {eval_result[cp]['reason']}")

        feedback = failed_reasons
        print(f"\nAttempt {attempt + 1} failed. Prepending {len(feedback)} corrective feedback items for next attempt.\n")
        attempt += 1

    final_attempt = history[-1]
    final_passed = final_attempt["result"]["overall_pass"]
    final_status = "PASSED" if final_passed else "SHIPPED_WITH_KNOWN_ISSUES"

    # Build rejection log entries for failed attempts (only failed ones, not the final passed one)
    rejection_entries: list[dict[str, Any]] = []
    for idx, item in enumerate(history):
        if not item["result"]["overall_pass"]:
            att_result = item["result"]
            failed_cps = [cp for cp in CHECKPOINT_KEYS if not att_result[cp]["pass"]]
            failure_details = {cp: att_result[cp]["reason"] for cp in failed_cps}

            # Detail what changed on the next try
            if idx + 1 < len(history):
                what_changed = (
                    f"Prompt updated for Attempt {idx + 2} with corrective instructions addressing: "
                    + ", ".join(failed_cps)
                )
            else:
                what_changed = "Retry budget exhausted. Logged for retrospective analysis."

            rejection_entries.append({
                "topic": topic,
                "attempt_number": item["attempt"] + 1,
                "timestamp": datetime.now().isoformat(),
                "failed_checkpoints": failed_cps,
                "failure_reasons": failure_details,
                "what_changed_on_next_try": what_changed,
            })

    # Save failed attempts to rejection log
    if rejection_entries:
        append_rejection_log(rejection_entries)

    # Save full run to data/runs/<timestamp>.json
    run_record = {
        "topic": topic,
        "final_status": final_status,
        "overall_pass": final_passed,
        "total_attempts": len(history),
        "created_at": datetime.now().isoformat(),
        "attempts": history,
    }
    run_file_path = save_run(run_record)

    # Save final lesson markdown file for easy copying
    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(FINAL_LESSON_FILE, "w", encoding="utf-8") as f:
        f.write(final_attempt["lesson"])

    # Also generate matching formatted PDF
    try:
        from pdf_generator import build_pdf
        pdf_path = os.path.splitext(FINAL_LESSON_FILE)[0] + ".pdf"
        build_pdf(topic, final_attempt["lesson"], pdf_path)
    except Exception as e:
        print(f"Warning: PDF generation failed: {e}")

    # Update cross-run memory with failure patterns
    update_memory_from_runs()

    return {
        "topic": topic,
        "final_status": final_status,
        "overall_pass": final_passed,
        "total_attempts": len(history),
        "final_lesson": final_attempt["lesson"],
        "run_file": run_file_path,
        "final_lesson_file": FINAL_LESSON_FILE,
        "rejection_log_file": REJECTION_LOG_FILE,
        "rejections": rejection_entries,
        "history": history,
    }


import os
from typing import Any
from google import genai

from config import MODEL_NAME, call_gemini_resilient, validate_api_key
from memory import load_memory


def build_generator_prompt(
    topic: str,
    feedback: list[str] | None = None,
    standing_instructions: list[str] | None = None,
) -> str:
    """Construct the prompt for generating a beginner-friendly lesson."""
    sections: list[str] = []

    # System instruction / role
    sections.append(
        "You are a master educator skilled at explaining complex technical concepts to complete beginners.\n"
        "Your task is to write a standalone lesson on the following topic:\n"
        f"TOPIC: {topic}\n"
    )

    # Core pedagogical guidelines
    sections.append(
        "TARGET AUDIENCE & PEDAGOGY RULES:\n"
        "1. ZERO BACKGROUND: The learner has no prior knowledge of computer science or AI.\n"
        "2. LANGUAGE: Use simple, plain English words and short, direct sentences. "
        "The learner is from a non-English-medium background. Avoid academic, dense, or pretentious phrasing.\n"
        "3. NO UNEXPLAINED JARGON: Do not use technical terms or acronyms without defining them in plain words first. "
        "If a technical term is necessary, explain what it means using simple everyday language immediately.\n"
        "4. REQUIRED CONTENT: Explicitly cover:\n"
        "   - WHAT IT IS: A simple, relatable definition.\n"
        "   - WHY IT MATTERS: The concrete problem it solves and why it is useful.\n"
        "   - HOW IT WORKS: Step-by-step explanation of the mechanism in simple words.\n"
        "5. TEACH BY EXAMPLE: Include at least one concrete, end-to-end relatable analogy or real-life worked example "
        "(e.g., an open-book exam, a chef consulting a recipe book, a librarian fetching files).\n"
        "6. COHERENT TEACHING FLOW: Organize with a clear Beginning (introduction/hook) -> Middle (explanation & example) -> End (recap & takeaway)."
    )

    # Cross-run standing instructions from memory
    if standing_instructions:
        instructions_text = "\n".join(f"- {inst}" for inst in standing_instructions)
        sections.append(
            f"STANDING INSTRUCTIONS (LEARNED FROM REPEATED PAST FAILURES):\n{instructions_text}"
        )

    # In-run feedback from previous attempt
    if feedback:
        feedback_text = "\n".join(f"- {item}" for item in feedback)
        sections.append(
            "CRITICAL CORRECTIONS (FIX PREVIOUS FAILED ATTEMPT):\n"
            "Your previous attempt failed evaluation for these specific reasons:\n"
            f"{feedback_text}\n"
            "Rewrite the lesson thoroughly, addressing and fixing every single one of these points."
        )

    # Deliberate error injection hook (useful for demonstration video)
    force_error = os.environ.get("FORCE_DELIBERATE_ERROR", "").strip().lower()
    if force_error in ("1", "true", "yes", "jargon") and not feedback:
        sections.append(
            "DEMO OVERRIDE: For this initial draft only, use heavy, unexplained technical jargon and dense academic vocabulary "
            "without defining terms, to test the evaluator's error-detection capabilities."
        )

    sections.append("Now write the complete lesson in clear, well-structured Markdown:")
    return "\n\n".join(sections)


def generate_lesson(
    topic: str,
    feedback: list[str] | None = None,
    client: Any = None,
) -> str:
    """
    Generate a beginner-friendly lesson on `topic`.
    Prepend previous feedback if provided, and incorporate cross-run memory instructions.
    """
    # 1. Load cross-run memory
    memory_data = load_memory()
    standing_instructions = memory_data.get("standing_instructions", [])

    # 2. Build prompt
    prompt = build_generator_prompt(topic, feedback, standing_instructions)

    # 3. Call Gemini
    if client is None:
        api_key = validate_api_key()
        client = genai.Client(api_key=api_key)

    return call_gemini_resilient(
        client=client,
        contents=prompt,
    )


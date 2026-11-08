# Build Guide — Self-Evaluating Lesson Content Generator (Gemini)

Hand this file to an AI coding agent (Claude Code, Cursor, etc.) and tell it to execute each chunk in order. It is scoped to exactly what the assessment requires — nothing extra.

Your only manual steps at the end: push to GitHub, record the video, and keep your Gemini API key out of the repo.

---

## Chunk 0 — Get a Gemini API key (you do this, 2 min)
1. Go to https://aistudio.google.com/app/apikey and create an API key (no credit card needed).
2. Copy your API key.
3. You will put it in a `.env` file as `GEMINI_API_KEY=your_key_here` (or `GOOGLE_API_KEY=your_key_here`). Never commit this file.

---

## Chunk 1 — Project scaffold
Agent instructions:
- Create a repo folder with this structure:
```
lesson-generator/
├── .env.example
├── .gitignore          # must ignore .env and any local db/log files you don't want tracked
├── requirements.txt    # google-genai, python-dotenv
├── README.md
├── config.py            # model name, retry limit, file paths
├── generator.py          # generate_lesson()
├── evaluator.py          # evaluate_lesson()
├── orchestrator.py       # run_pipeline() — the main loop
├── memory.py             # load/save run history + rejection logs
├── main.py               # CLI entry point: python main.py "Introduction to RAG"
├── data/
│   ├── runs/              # one JSON file per run, auto-created
│   └── memory.json        # cross-run learned notes, auto-created
└── logs/
    └── rejection_log.json # structured log of every failed attempt across all runs
```
- `requirements.txt` contents: `google-genai`, `python-dotenv`.
- `.env.example` contents: `GEMINI_API_KEY=your_key_here`
- `.gitignore` must include `.env`, `__pycache__/`, `*.pyc`.

---

## Chunk 2 — Config (`config.py`)
Define constants:
- `GEMINI_API_KEY`: loaded from environment variable `GEMINI_API_KEY` (or fallback `GOOGLE_API_KEY`)
- `MODEL_NAME = "gemini-3.8-flash"` (Google's latest general-purpose model; fallback to other flash models if rate-limited or preferred)
- `MAX_RETRIES = 2` (hard cap so the loop always terminates — per the brief's "1–2 retries")
- `DATA_DIR = "data"`
- `RUNS_DIR = "data/runs"`
- `MEMORY_FILE = "data/memory.json"`
- `LOGS_DIR = "logs"`
- `REJECTION_LOG_FILE = "logs/rejection_log.json"`
- `FINAL_LESSON_FILE = "data/runs/final_lesson.md"`

---

## Chunk 3 — Generator (`generator.py`)
Function: `generate_lesson(topic: str, feedback: list[str] | None = None) -> str`

Behavior:
- Calls the Google GenAI SDK (`from google import genai; client = genai.Client(api_key=GEMINI_API_KEY)`, `client.models.generate_content(model=MODEL_NAME, contents=...)`).
- System/user prompt must instruct the model to:
  - Write a standalone beginner lesson on `topic` for someone with **zero background**, limited English vocabulary, and a non-English-medium education (plain words, short sentences, no unexplained jargon).
  - Cover: what it is, why it matters, how it works.
  - Include at least one concrete example or analogy (to satisfy "teaches by example").
  - Have a clear beginning → middle → end structure (to satisfy "coherent teaching flow").
- If `feedback` is passed (from a previous failed evaluation), prepend it to the prompt as explicit instructions to fix, e.g.: *"Your previous attempt failed these checks for these reasons: [...]. Rewrite the lesson and fix every one of these issues."*
- Calls `load_memory()` from `memory.py` to check for standing instructions learned from past runs and includes them in the prompt.
- Returns the lesson text (string).

---

## Chunk 4 — Evaluator (`evaluator.py`)
Function: `evaluate_lesson(topic: str, lesson: str) -> dict`

Behavior:
- Calls Gemini API as a strict grader and returns **structured JSON only**, with one pass/fail (`true`/`false`) per checkpoint plus a short reason:
```json
{
  "accurate_and_grounded": {"pass": true, "reason": "..."},
  "beginner_friendly_language": {"pass": false, "reason": "..."},
  "teaches_by_example": {"pass": true, "reason": "..."},
  "no_unexplained_jargon": {"pass": true, "reason": "..."},
  "covers_key_points": {"pass": true, "reason": "..."},
  "coherent_teaching_flow": {"pass": true, "reason": "..."},
  "overall_pass": false
}
```
- Each checkpoint maps directly to the 6 dimensions named in the brief:
  1. `accurate_and_grounded` (Technical accuracy & grounded facts)
  2. `beginner_friendly_language` (Simple words, short sentences, no assumed knowledge)
  3. `teaches_by_example` (At least one concrete end-to-end example or analogy)
  4. `no_unexplained_jargon` (Every technical term defined in simple words before use)
  5. `covers_key_points` (What it is, why it matters, how it works)
  6. `coherent_teaching_flow` (Beginning -> middle -> end structure, standalone outcome)
- No partial credit — each is strictly true/false.
- `overall_pass` is computed deterministically in code: `true` only if **all six** are `true`.
- Parse the model's JSON output defensively (strip markdown fences, handle malformed JSON by retrying the API call once).
- Return the parsed dict.

---

## Chunk 5 — Orchestrator (`orchestrator.py`)
Function: `run_pipeline(topic: str) -> dict`

Logic:
1. `attempt = 0`, `feedback = None`, `history = []`
2. Loop:
   - `lesson = generate_lesson(topic, feedback)`
   - `result = evaluate_lesson(topic, lesson)`
   - Append `{attempt, lesson, result}` to `history`
   - If `result["overall_pass"]` is `True` → break (success)
   - If `attempt >= MAX_RETRIES` → break (exhausted retries — ship best attempt or last attempt, and flag it as such)
   - Else: build `feedback` = list of `reason` strings for every checkpoint that failed; `attempt += 1`
3. Write every failed attempt (not the final successful one) to `logs/rejection_log.json` via `memory.py`, in the format: what failed, why, what changed on the next try (diff the feedback given vs. what changed in the next generated lesson — at minimum, log the feedback text itself as "what changed").
4. Save the full run (topic, all attempts, final status) to `data/runs/<timestamp>.json` via `memory.py`.
5. Update cross-run memory in `data/memory.json` with failure trends.
6. Return the final lesson + pass/fail summary + rejection log entries for this run.

---

## Chunk 6 — Memory (`memory.py`)
Two responsibilities:

**a) Per-run persistence** (satisfies "output: rejection log")
- `save_run(run_data: dict)` → writes to `data/runs/<timestamp>.json`
- `append_rejection_log(entries: list[dict])` → appends to `logs/rejection_log.json`

**b) Cross-run learning** (satisfies "self-evolving" + "memory persists across runs")
- `load_memory() -> dict` / `save_memory(data: dict)` on `data/memory.json`.
- After each run, aggregate which checkpoints have failed most often across **all** past runs (read all files in `data/runs/`).
- If a specific checkpoint (e.g., `beginner_friendly_language`) has failed in >1 past run, add a standing instruction to the generator's system prompt for future runs, e.g.: *"Note: past lessons have repeatedly failed on beginner-friendly language — use shorter sentences and avoid technical terms without a plain-language definition."*
- `generator.py`'s `generate_lesson()` calls `load_memory()` and includes any such standing instructions in its prompt, on top of the in-run `feedback` from Chunk 3. This is what makes the system "learn from repeated failures to sharpen prompts" across runs, not just within one run's retries.

---

## Chunk 7 — CLI entry point (`main.py`)
- Accepts topic as a command-line argument: `python main.py "Introduction to RAG (Retrieval-Augmented Generation)"`
- Loads `.env` (`python-dotenv`), runs `run_pipeline(topic)`, prints:
  - Final pass/fail status
  - Number of attempts taken
  - Path to the saved lesson and rejection log
- Also save the final passing lesson as a plain `.md` file (`data/runs/final_lesson.md`) so it's easy to copy into the required Google Doc.

---

## Chunk 8 — README.md
Must include:
1. What the project does (one paragraph, matches the brief).
2. Setup: clone repo → `pip install -r requirements.txt` → copy `.env.example` to `.env` → add your Gemini key.
3. Run: `python main.py "Introduction to RAG"`.
4. Where outputs land: final lesson (`data/runs/final_lesson.md`), rejection log (`logs/rejection_log.json`), full run history (`data/runs/`).
5. Short note on architecture: generate → evaluate → regenerate (max 2 retries) → output, plus how cross-run memory works.
6. Note on how to reproduce the "evaluator catches a deliberate error" demo (see Chunk 9).

---

## Chunk 9 — Test runs (for the video, you do this)
1. **Clean run:** `python main.py "Introduction to RAG (Retrieval-Augmented Generation)"` — let it pass normally. This produces the final submission lesson.
2. **Deliberate-error run (for the video's required "evaluator catching a deliberate error" segment):** Temporarily edit `generator.py` to force a bad first draft — e.g., add a hardcoded instruction like *"Use advanced technical jargon without explaining it"* only on `attempt == 0`. Run the pipeline, screen-record it: the evaluator should fail that attempt on `beginner_friendly_language` and/or `no_unexplained_jargon`, feedback gets fed back, and attempt 2 passes. Then revert the temporary edit before your final commit.

---

## Chunk 10 — Final submission checklist (you do this)
- [ ] Clean run of "Introduction to RAG" produces a passing lesson (all 6 checkpoints true).
- [ ] `logs/rejection_log.json` has at least one real failed-attempt entry with reasons + what changed.
- [ ] `.env` is NOT committed; `.env.example` is.
- [ ] Push repo to GitHub, README is accurate and someone else could run it from scratch.
- [ ] Copy the final lesson text into a Google Doc, get a shareable link.
- [ ] Record 15–20 min Loom (or OBS + unlisted YouTube/Drive link if Loom's free tier is too short), face visible, covering: full pipeline running end-to-end, the deliberate-error evaluator catch, and a spoken walkthrough of how the code works.
- [ ] Submit via the form: GitHub link, Doc link, video link.

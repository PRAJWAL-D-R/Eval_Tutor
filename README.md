# Self-Evaluating Lesson Generator

An autonomous pedagogical content generation pipeline with deterministic rubric evaluation and automated self-correction loops.

The system accepts a technical topic, generates a lesson structured for beginners, evaluates the draft against six binary quality checkpoints using structured model outputs, and automatically refines the draft using targeted feedback if any checkpoint fails.

---

## Architecture and Design

### System Overview

The pipeline separates generation, evaluation, orchestration, and persistence into distinct modules. It enforces an explicit quality contract: rather than relying on self-reported quality scores from the generation model, a separate evaluation pass scores each checkpoint with a binary boolean and a grounded rationale. Final acceptance is calculated deterministically in application code (`all(checkpoints == True)`).



```
                      +-------------------+
                      |    Topic Input    |
                      +---------+---------+
                                |
                                v
               +----------------------------------+
        +----->|  Draft Generator (generator.py)  |<------+
        |      |  - Applies pedagogical rules    |       |
        |      |  - Incorporates past memory      |       |
        |      +----------------+-----------------+       |
        |                       |                         |
        |                       v                         |
        |      +----------------------------------+       |
        |      |    Evaluator (evaluator.py)      |       |
        |      |  - 6 binary rubric checkpoints   |       |
        |      |  - Deterministic Python gate     |       |
        |      +----------------+-----------------+       |
        |                       |                         |
Targeted|                [Pass or Fail?]                  |
Feedback|                       |                         |
        |             +---------+---------+               |
        |             |                   |               |
        |           Fail                 Pass             |
        |     (Retries remain)            |               |
        +-------------+                   |               |
                      |                   v               |
                      |     +---------------------------+ |
                      |     |  Orchestrator Finalize    | |
                      |     |  - Save run history (JSON)| |
                      |     |  - Export Markdown & PDF  | |
                      |     +-------------+-------------+ |
                      |                   |               |
                      v                   v               |
           +--------------------+ +---------------------+ |
           | logs/rejection_log | |  data/memory.json   |-+
           | (Failure audit)    | |  (Standing patterns)|
           +--------------------+ +---------------------+
```

### Execution Flow

1. **Context Initialization**: The orchestrator queries `data/memory.json` for standing pedagogical instructions derived from past run failures.
2. **Draft Generation**: The generator calls Google Gemini (`gemini-3.5-flash-lite`) to produce a beginner-friendly lesson covering What, Why, and How, accompanied by a real-world analogy.
3. **Structured Evaluation**: The evaluator assesses the draft against six binary criteria, returning structured JSON with boolean flags and evidence-based rationales.
4. **Deterministic Gate**: Python verifies that all six checkpoints evaluated to `true`. If all pass, the draft is marked ready for publication.
5. **Self-Correction Loop**: If one or more checkpoints fail and retry attempts remain (up to `MAX_RETRIES = 2`), the specific failure reasons are prepended to the prompt as required corrections for the subsequent generation attempt.
6. **Persistence & Auditing**:
   - Each attempt, draft, and evaluation score is recorded in `data/runs/<timestamp>.json`.
   - Every failed attempt is appended to `logs/rejection_log.json` with checkpoint diffs.
   - Recurring checkpoint failure patterns update standing instructions in `data/memory.json`.
   - The final passing lesson is exported to both Markdown (`data/runs/final_lesson.md`) and publication-ready PDF (`data/runs/final_lesson.pdf`).

---

### Core Modules

| Module | File | Responsibility |
|---|---|---|
| Configuration | `config.py` | API client setup, model defaults, fallbacks, retry parameters, and exponential backoff. |
| Generator | `generator.py` | Prompt construction, pedagogical constraints, memory injection, and feedback integration. |
| Evaluator | `evaluator.py` | Rubric definition, structured JSON scoring, schema validation, and deterministic passing gate. |
| Memory | `memory.py` | Run logging, rejection audit recording, and cross-run pattern extraction. |
| Orchestrator | `orchestrator.py` | Procedural execution loop, retry budget management, and export generation. |
| PDF Engine | `pdf_generator.py` | Server-side PDF compilation via ReportLab with typography formatting and page numbering. |
| Dashboard | `ui.py` | Local HTTP dashboard with real-time SSE streaming of agent thinking and evaluation status. |
| CLI Entrypoint | `main.py` | Terminal interface for automated runs and pipeline execution. |

---

### The Six Rubric Checkpoints

To ensure content quality, every draft must satisfy all six checkpoints. Partial credit is not accepted.

| Checkpoint Key | Name | Requirement |
|---|---|---|
| `accurate_and_grounded` | Technical Accuracy | Explanations, mechanisms, and architectural facts must be technically correct without hallucinations. |
| `beginner_friendly_language` | Beginner Accessibility | Uses plain language and short sentences; avoids assumed technical background. |
| `teaches_by_example` | Relatable Analogy | Must include at least one concrete, end-to-end everyday analogy or worked scenario. |
| `no_unexplained_jargon` | Zero Unexplained Jargon | Technical terms and acronyms must be defined in plain terms before or at first mention. |
| `covers_key_points` | Core Structural Pillars | Explicitly covers What it is, Why it is needed, and How it operates step-by-step. |
| `coherent_teaching_flow` | Pedagogical Progression | Follows a clear progression: Introduction, Core Concept, Concrete Walkthrough, and Takeaways. |

---

## Prerequisites

- Python 3.10 or higher
- A Google Gemini API Key (available free from [Google AI Studio](https://aistudio.google.com/app/apikey))

---

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai_tutor
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   *On Windows:*
   ```cmd
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Copy the example environment file and insert your API key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```ini
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

---

## Running the Application

### Option 1: Interactive Web Dashboard

Launch the local web server:
```bash
python ui.py
```
Open your browser to `http://localhost:8000`.

Features:
- **Left Panel:** Live agent execution logs, attempt counters, rubric scorecard with pass/fail badges, and corrective feedback diffs.
- **Right Panel:** Rendered final lesson in Markdown with options to copy raw text or download as a formatted PDF.
- **Deliberate Error Toggle:** Checkbox to simulate a failure and observe real-time self-healing.
- **Resizable Layout:** Draggable separator bar between thinking and output panels.

### Option 2: Command-Line Interface

Run generation directly from your terminal:
```bash
python main.py "Introduction to RAG (Retrieval-Augmented Generation)"
```

You can pass any custom technical topic as an argument:
```bash
python main.py "Introduction to Vector Databases"
```

### Option 3: Deliberate Defect Demonstration (Audit Verification)

To verify that the evaluation engine detects non-compliant content and forces a self-correcting retry loop, trigger the deliberate error mode:

```bash
FORCE_DELIBERATE_ERROR=1 python main.py "Introduction to RAG (Retrieval-Augmented Generation)"
```

Execution sequence in this mode:
1. **Attempt 1:** A prompt override injects dense, unexplained academic terminology into the initial draft.
2. **Evaluation:** The evaluator flags failures on `beginner_friendly_language` and `no_unexplained_jargon`.
3. **Audit Log:** The failure is written to `logs/rejection_log.json`.
4. **Attempt 2:** The orchestrator prepends the evaluator's specific critique as mandatory correction rules.
5. **Pass:** Attempt 2 generates clean, analogy-driven content and passes all six checks.

---

## Automated Testing

Run the test suite to verify evaluation logic, prompt formation, persistence schemas, and retry loops without making live API calls:

```bash
python -m unittest tests/test_pipeline.py
```

Test coverage includes:
- Strict binary validation and deterministic Python scoring.
- Defensive JSON extraction across markdown-fenced responses.
- Prompt construction with feedback prepending on retries.
- Cross-run memory aggregation and threshold triggers.
- End-to-end mocked pipeline execution through retry recovery.

---

## Output and Data Layout

Generated outputs and audit logs are saved to standard project directories:

```
ai_tutor/
├── data/
│   ├── memory.json             # Cross-run failure patterns and standing rules
│   └── runs/
│       ├── <timestamp>.json    # Complete attempt history and scoring for each run
│       ├── final_lesson.md     # Latest passing lesson in Markdown
│       └── final_lesson.pdf    # Latest passing lesson formatted as PDF
├── logs/
│   └── rejection_log.json      # Structured log of every rejected draft and reason
├── tests/
│   └── test_pipeline.py       # Unit tests for the pipeline
├── config.py                   # Model configuration and retry parameters
├── evaluator.py                # 6-checkpoint rubric evaluation logic
├── generator.py                # Pedagogical content generator
├── main.py                     # CLI entrypoint
├── memory.py                   # Run history and memory storage engine
├── orchestrator.py             # Pipeline loop controller
├── pdf_generator.py            # ReportLab PDF compiler
└── ui.py                       # Local dashboard server
```

---

## Configuration Reference

Key settings can be modified in `config.py` or `.env`:

| Setting | Default Value | Description |
|---|---|---|
| `GEMINI_API_KEY` | None (Required) | Google AI Studio API key. |
| `MODEL_NAME` | `gemini-3.5-flash-lite` | Primary model used for generation and evaluation. |
| `FALLBACK_MODELS` | `["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash"]` | Fallback models tried if primary encounters rate limits. |
| `MAX_RETRIES` | `2` | Maximum retry attempts per topic run (3 attempts total). |
| `TEMPERATURE` | `0.4` | Sampling temperature for balanced creativity and adherence. |
| `PORT` | `8000` | Port for the local web dashboard. |

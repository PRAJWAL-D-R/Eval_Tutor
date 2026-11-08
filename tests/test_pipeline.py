import json
import os
import shutil
import tempfile
import unittest

import config
import evaluator
import generator
import memory
import orchestrator


class TestPipeline(unittest.TestCase):
    def setUp(self):
        # Create a temporary sandbox directory for test runs and logs
        self.test_dir = tempfile.mkdtemp()
        self.orig_runs_dir = config.RUNS_DIR
        self.orig_memory_file = config.MEMORY_FILE
        self.orig_logs_dir = config.LOGS_DIR
        self.orig_rejection_file = config.REJECTION_LOG_FILE
        self.orig_final_lesson = config.FINAL_LESSON_FILE

        # Point paths to temp directory
        memory.RUNS_DIR = os.path.join(self.test_dir, "runs")
        memory.MEMORY_FILE = os.path.join(self.test_dir, "memory.json")
        memory.LOGS_DIR = os.path.join(self.test_dir, "logs")
        memory.REJECTION_LOG_FILE = os.path.join(memory.LOGS_DIR, "rejection_log.json")

        orchestrator.RUNS_DIR = memory.RUNS_DIR
        orchestrator.FINAL_LESSON_FILE = os.path.join(memory.RUNS_DIR, "final_lesson.md")
        orchestrator.REJECTION_LOG_FILE = memory.REJECTION_LOG_FILE

    def tearDown(self):
        # Restore paths and clean up temp directory
        memory.RUNS_DIR = self.orig_runs_dir
        memory.MEMORY_FILE = self.orig_memory_file
        memory.LOGS_DIR = self.orig_logs_dir
        memory.REJECTION_LOG_FILE = self.orig_rejection_file

        orchestrator.RUNS_DIR = self.orig_runs_dir
        orchestrator.FINAL_LESSON_FILE = self.orig_final_lesson
        orchestrator.REJECTION_LOG_FILE = self.orig_rejection_file

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_prompt_construction(self):
        """Test generator prompt includes pedagogy rules, feedback, and memory."""
        prompt = generator.build_generator_prompt(
            topic="Introduction to RAG",
            feedback=["Explain embedding in plain words", "Add an analogy"],
            standing_instructions=["Keep sentences short"],
        )
        self.assertIn("Introduction to RAG", prompt)
        self.assertIn("Explain embedding in plain words", prompt)
        self.assertIn("Add an analogy", prompt)
        self.assertIn("Keep sentences short", prompt)
        self.assertIn("TARGET AUDIENCE & PEDAGOGY RULES", prompt)

    def test_evaluator_json_extraction(self):
        """Test defensive parsing of markdown code fences and raw json."""
        raw_with_fences = """```json
{
  "accurate_and_grounded": {"pass": true, "reason": "Accurate facts"},
  "beginner_friendly_language": {"pass": true, "reason": "Simple terms"},
  "teaches_by_example": {"pass": true, "reason": "Good analogy"},
  "no_unexplained_jargon": {"pass": true, "reason": "Clear definitions"},
  "covers_key_points": {"pass": true, "reason": "What why how present"},
  "coherent_teaching_flow": {"pass": true, "reason": "Good narrative"},
  "overall_pass": true
}
```"""
        parsed = evaluator.extract_json_from_response(raw_with_fences)
        validated = evaluator.validate_evaluation_dict(parsed)
        self.assertTrue(validated["overall_pass"])
        for cp in evaluator.CHECKPOINT_KEYS:
            self.assertTrue(validated[cp]["pass"])

    def test_evaluator_deterministic_pass(self):
        """Test that deterministic logic overrides model's reported overall_pass if any check failed."""
        raw_bad = {
            "accurate_and_grounded": {"pass": True, "reason": "Accurate"},
            "beginner_friendly_language": {"pass": False, "reason": "Too many big words"},
            "teaches_by_example": {"pass": True, "reason": "Has example"},
            "no_unexplained_jargon": {"pass": True, "reason": "No jargon"},
            "covers_key_points": {"pass": True, "reason": "Covered"},
            "coherent_teaching_flow": {"pass": True, "reason": "Flow is fine"},
            "overall_pass": True,  # Model mistakenly claimed true
        }
        validated = evaluator.validate_evaluation_dict(raw_bad)
        self.assertFalse(validated["overall_pass"], "overall_pass must be False if any checkpoint fails")

    def test_memory_and_rejection_logging(self):
        """Test saving run, rejection log, and cross-run memory aggregation."""
        run_data = {
            "topic": "Test Run",
            "attempts": [
                {
                    "attempt": 0,
                    "lesson": "Bad draft",
                    "result": {
                        "beginner_friendly_language": {"pass": False, "reason": "Too complex"},
                        "no_unexplained_jargon": {"pass": True, "reason": "OK"},
                        "overall_pass": False,
                    },
                }
            ],
        }
        saved_path = memory.save_run(run_data)
        self.assertTrue(os.path.exists(saved_path))

        memory.append_rejection_log([{"attempt": 1, "reason": "Too complex"}])
        self.assertTrue(os.path.exists(memory.REJECTION_LOG_FILE))

        # Add a second run with same failure to test >1 failure triggering standing instruction
        run_data_2 = {
            "topic": "Test Run 2",
            "attempts": [
                {
                    "attempt": 0,
                    "lesson": "Another bad draft",
                    "result": {
                        "beginner_friendly_language": {"pass": False, "reason": "Too dense"},
                        "overall_pass": False,
                    },
                }
            ],
        }
        memory.save_run(run_data_2)

        mem = memory.update_memory_from_runs()
        self.assertEqual(mem["checkpoint_failure_counts"]["beginner_friendly_language"], 2)
        self.assertGreater(len(mem["standing_instructions"]), 0)
        self.assertIn("beginner-friendly", mem["standing_instructions"][0])

    def test_orchestrator_pipeline_flow(self):
        """Test orchestrator execution flow with simulated failure on attempt 0 and success on attempt 1."""
        calls = []

        def mock_gen(topic, feedback=None):
            calls.append(feedback)
            if len(calls) == 1:
                return "Draft 1 with technical jargon"
            return "Draft 2 with simple words and analogy"

        def mock_eval(topic, lesson):
            if "technical jargon" in lesson:
                return {
                    "accurate_and_grounded": {"pass": True, "reason": "Good"},
                    "beginner_friendly_language": {"pass": False, "reason": "Jargon used"},
                    "teaches_by_example": {"pass": True, "reason": "Good"},
                    "no_unexplained_jargon": {"pass": False, "reason": "Defined poorly"},
                    "covers_key_points": {"pass": True, "reason": "Good"},
                    "coherent_teaching_flow": {"pass": True, "reason": "Good"},
                    "overall_pass": False,
                }
            return {
                "accurate_and_grounded": {"pass": True, "reason": "Good"},
                "beginner_friendly_language": {"pass": True, "reason": "Plain words"},
                "teaches_by_example": {"pass": True, "reason": "Clear analogy"},
                "no_unexplained_jargon": {"pass": True, "reason": "Terms defined"},
                "covers_key_points": {"pass": True, "reason": "All 3 points covered"},
                "coherent_teaching_flow": {"pass": True, "reason": "Clear narrative"},
                "overall_pass": True,
            }

        result = orchestrator.run_pipeline("Pipeline Test", generator_fn=mock_gen, evaluator_fn=mock_eval)
        self.assertEqual(result["total_attempts"], 2)
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["final_status"], "PASSED")
        self.assertTrue(os.path.exists(result["final_lesson_file"]))
        self.assertTrue(os.path.exists(result["run_file"]))
        self.assertEqual(len(result["rejections"]), 1)
        self.assertIn("beginner_friendly_language", result["rejections"][0]["failed_checkpoints"])


if __name__ == "__main__":
    unittest.main()


import os
import sys
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from config import FINAL_LESSON_FILE, REJECTION_LOG_FILE, validate_api_key
from orchestrator import run_pipeline


def main() -> None:
    # 1. Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print("Usage: python main.py [TOPIC]")
            print('Example: python main.py "Introduction to RAG (Retrieval-Augmented Generation)"')
            sys.exit(0)
        topic = " ".join(sys.argv[1:]).strip()
    else:
        topic = "Introduction to RAG (Retrieval-Augmented Generation)"
        print(f"No topic provided on command line. Using default submission topic: '{topic}'")

    # 2. Check for Gemini API key
    try:
        validate_api_key()
    except ValueError as e:
        print(f"\n[ERROR] Configuration Issue:\n{e}\n")
        print("Steps to resolve:")
        print("1. Copy .env.example to .env:  cp .env.example .env")
        print("2. Get a key at https://aistudio.google.com/app/apikey")
        print("3. Paste it into .env: GEMINI_API_KEY=AIzaSy...")
        sys.exit(1)

    # 3. Execute pipeline
    try:
        result = run_pipeline(topic)
    except Exception as e:
        print(f"\n[ERROR] Pipeline execution failed: {e}")
        sys.exit(1)

    # 4. Print clean summary report
    print("\n" + "=" * 60)
    print("                PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Topic:             {result['topic']}")
    print(f"Final Status:      {result['final_status']}")
    print(f"All Checks Passed: {'YES (Ship Ready)' if result['overall_pass'] else 'NO (Shipped with Known Issues)'}")
    print(f"Attempts Taken:    {result['total_attempts']}")
    print("-" * 60)
    print(f"Final Lesson MD:   {result['final_lesson_file']}")
    print(f"Full Run Record:   {result['run_file']}")
    if os.path.exists(REJECTION_LOG_FILE):
        print(f"Rejection Log:     {REJECTION_LOG_FILE}")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the final lesson in 'data/runs/final_lesson.md'.")
    print("2. Copy the lesson text to your submission Google Doc.")
    print("3. Check 'logs/rejection_log.json' to review logged rejections.\n")


if __name__ == "__main__":
    main()


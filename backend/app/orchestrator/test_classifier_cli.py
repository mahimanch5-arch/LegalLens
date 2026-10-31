#!/usr/bin/env python3
"""
Manual testing script for Intent Classifier

Usage:
    python test_classifier_cli.py              # Interactive mode
    python test_classifier_cli.py --batch      # Run test suite
    python test_classifier_cli.py "your message here"  # Single classification
"""

import argparse
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from the same directory as this script
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


from intent_classifier import Intent, IntentClassifier  # noqa: E402  (.env must load first)


def print_result(message: str, result: Any) -> None:
    """Pretty print a classification result"""
    print(f"\n{'='*70}")
    print(f"Message: {message}")
    print(f"{'-'*70}")
    print(f"Intent:        {result.intent.value.upper()}")
    print(f"Confidence:    {result.confidence:.1%}")
    print(f"Method:        {'Heuristic' if result.used_heuristic else 'LLM (Claude Haiku)'}")
    print(f"Reason:        {result.reason}")
    print(f"{'='*70}")


def interactive_mode() -> None:
    """Interactive classification mode"""
    print("\n🤖 LegalLens Intent Classifier - Interactive Mode")
    print("=" * 70)
    print("Enter user messages to classify their intent.")
    print("Commands:")
    print("  'quit' or 'exit' - Exit the program")
    print("  'help' - Show this help message")
    print("=" * 70 + "\n")

    classifier = IntentClassifier()

    while True:
        try:
            message = input("📝 Enter message (or 'quit'): ").strip()

            if not message:
                continue

            if message.lower() in ['quit', 'exit']:
                print("\n👋 Goodbye!")
                break

            if message.lower() == 'help':
                print("\nAvailable intents:")
                for intent in Intent:
                    print(f"  - {intent.value}")
                print()
                continue

            result = classifier.classify(message)
            print_result(message, result)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.\n")


def batch_mode() -> bool:
    """Run predefined test cases"""
    print("\n🤖 LegalLens Intent Classifier - Batch Test Mode")
    print("=" * 70 + "\n")

    classifier = IntentClassifier()

    test_cases = [
        # Ask intent
        ("What are the termination rights?", Intent.ASK),
        ("When does the contract expire?", Intent.ASK),
        ("How much notice must be given?", Intent.ASK),
        ("Are there non-compete clauses?", Intent.ASK),
        ("Can you explain the indemnification?", Intent.ASK),
        ("Tell me about the payment terms", Intent.ASK),

        # Summary intent
        ("Summarize this contract", Intent.SUMMARY),
        ("Give me an overview of this opinion", Intent.SUMMARY),
        ("What are the key points?", Intent.SUMMARY),
        ("Extract the main terms", Intent.SUMMARY),
        ("Summarize and extract key information", Intent.SUMMARY),

        # Draft intent
        ("Draft a memo on indemnification", Intent.DRAFT),
        ("Write a case brief for this opinion", Intent.DRAFT),
        ("Create a memo analyzing the termination clause", Intent.DRAFT),
        ("Generate a brief summarizing the holding", Intent.DRAFT),
        ("Prepare a memorandum on the pricing", Intent.DRAFT),

        # Edge cases
        ("xyz", Intent.ASK),
        ("draft a summary", Intent.DRAFT),  # Draft takes priority
        ("What is a good case brief?", Intent.ASK),  # Asking about, not requesting
    ]

    passed = 0
    failed = 0

    for message, expected_intent in test_cases:
        result = classifier.classify(message)

        is_correct = result.intent == expected_intent
        symbol = "✅" if is_correct else "❌"

        status = "PASS" if is_correct else "FAIL"
        print(f"{symbol} [{status}] {message[:50]:50} → {result.intent.value:10} (expected: {expected_intent.value})")

        if is_correct:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print(f"{'='*70}\n")

    return failed == 0


def single_classification(message: str) -> None:
    """Classify a single message"""
    classifier = IntentClassifier()
    result = classifier.classify(message)
    print_result(message, result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual testing script for LegalLens Intent Classifier"
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="Single message to classify"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch tests instead of interactive mode"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        import os
        os.environ["INTENT_CLASSIFIER_DEBUG"] = "true"

    if args.batch:
        success = batch_mode()
        sys.exit(0 if success else 1)
    elif args.message:
        single_classification(args.message)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()

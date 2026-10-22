#!/usr/bin/env python3
"""Task 2 - driver program for the ``grades`` module.

Demonstrates importing and using the modular functions from ``grades.py``.
Run with ``--demo`` for a sample class, otherwise it starts an interactive
prompt where you enter students and their scores.
"""

from __future__ import annotations

import argparse

from grades import (
    StudentRecord,
    class_summary,
    render_report,
    summarize_all,
    validate_score,
)

SAMPLE_STUDENTS: list[dict] = [
    {"name": "Amara", "scores": [88, 92, 95, 79]},
    {"name": "Bekele", "scores": [45, 52, 38, 61]},
    {"name": "Chidi", "scores": [100, 98, 91]},
    {"name": "Desta", "scores": [70, 65, 72, 68]},
    {"name": "Fatima", "scores": [30, 41, 55]},
]


def print_summary(records: list[StudentRecord]) -> None:
    """Print the per-student table plus the class aggregate."""
    reports = summarize_all(records)
    print()
    print(render_report(reports))

    summary = class_summary(records)
    print()
    print(f"{'=' * 52}")
    print(f"Students:       {summary['students']}")
    print(f"Passed:         {summary['passed']}")
    print(f"Failed:         {summary['failed']}")
    print(f"Pass rate:      {summary['pass_rate']:.1f}%")
    print(f"Class average:  {summary['class_average']:.2f}")
    print(f"Top student:    {summary['top_student']}")
    print(f"{'=' * 52}")


def run_demo() -> None:
    """Run the processor against the built-in sample class."""
    records = [StudentRecord.from_mapping(student) for student in SAMPLE_STUDENTS]
    print("Task 2 - Student Grade Processor (demo data)")
    print_summary(records)


def parse_score(raw: str) -> float:
    """Convert raw text into a validated 0-100 score, with a friendly error."""
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"'{raw}' is not a number.") from None
    return validate_score(value)


def run_interactive() -> None:
    """Collect students and scores from the user, then report."""
    print("Task 2 - Student Grade Processor (interactive)")
    print("Enter a blank name to finish.\n")

    records: list[StudentRecord] = []

    while True:
        name = input("Student name: ").strip()
        if not name:
            break

        scores: list[float] = []
        print(f"  Enter scores for {name} (blank line to move on):")
        while True:
            raw = input("    score: ").strip()
            if raw == "":
                break
            try:
                scores.append(parse_score(raw))
            except ValueError as exc:
                print(f"    [error] {exc}")

        if not scores:
            print(f"  [skip] No valid scores entered for {name}.")
            continue

        try:
            records.append(StudentRecord(name=name, scores=scores))
        except ValueError as exc:
            print(f"  [error] {exc}")

    if not records:
        print("\nNo students entered - nothing to report.")
        return

    print_summary(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Student Grade Processor")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run against the built-in sample class instead of prompting.",
    )
    args = parser.parse_args()

    try:
        if args.demo:
            run_demo()
        else:
            run_interactive()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted.")


if __name__ == "__main__":
    main()

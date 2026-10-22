#!/usr/bin/env python3
"""Task 1 - CLI Expense Tracker with Persistent Storage.

A command-line expense tracker that accepts user input for amount, category and
date. Entries are held in memory as a list of dictionaries for the duration of
the session and persisted to a local JSON file so that data survives between
runs and is reloaded on startup.

Covered topics:
    Variables & Data Types | Lists & Dictionaries | File I/O | Basic CLI Design

Bonus:
    Monthly summary report using f-strings and basic aggregation
    (total spend and average spend per category).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_FILE: Path = Path(__file__).resolve().parent / "expenses.json"

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "utilities",
    "entertainment",
    "health",
    "other",
)

DATE_FORMAT = "%Y-%m-%d"


# --------------------------------------------------------------------------- #
# Persistence: JSON file I/O
# --------------------------------------------------------------------------- #
def load_expenses(path: Path = DATA_FILE) -> list[dict[str, Any]]:
    """Load expenses from ``path``.

    Returns an empty list when the file is missing or cannot be parsed so the
    program always starts in a usable state.
    """
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[warning] Could not read {path.name} ({exc}). Starting with an empty ledger.")
        return []

    if not isinstance(data, list):
        print(f"[warning] {path.name} did not contain a list of expenses. Starting with an empty ledger.")
        return []

    return [entry for entry in data if isinstance(entry, dict)]


def save_expenses(expenses: list[dict[str, Any]], path: Path = DATA_FILE) -> None:
    """Persist ``expenses`` to ``path`` as indented JSON."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(expenses, handle, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def parse_amount(raw: str) -> float:
    """Convert user input into a positive, two-decimal float amount."""
    try:
        amount = float(raw.strip())
    except (ValueError, AttributeError):
        raise ValueError("Amount must be a number, e.g. 12.50") from None

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    return round(amount, 2)


def parse_date(raw: str) -> str:
    """Validate a date string and normalise it to ``YYYY-MM-DD``."""
    try:
        parsed = datetime.strptime(raw.strip(), DATE_FORMAT)
    except (ValueError, AttributeError):
        raise ValueError("Date must be in YYYY-MM-DD format, e.g. 2026-10-19") from None

    return parsed.date().isoformat()


def parse_category(raw: str) -> str:
    """Normalise a category name to lowercase, rejecting empty input."""
    category = raw.strip().lower()
    if not category:
        raise ValueError("Category cannot be empty.")
    return category


def next_id(expenses: list[dict[str, Any]]) -> int:
    """Return the next unused integer id."""
    return max((entry.get("id", 0) for entry in expenses), default=0) + 1


# --------------------------------------------------------------------------- #
# Core operations
# --------------------------------------------------------------------------- #
def add_expense(
    expenses: list[dict[str, Any]],
    amount: float,
    category: str,
    date_str: str,
) -> dict[str, Any]:
    """Append a new expense to ``expenses`` and return the created entry."""
    entry: dict[str, Any] = {
        "id": next_id(expenses),
        "amount": amount,
        "category": category,
        "date": date_str,
    }
    expenses.append(entry)
    return entry


def delete_expense(expenses: list[dict[str, Any]], expense_id: int) -> dict[str, Any] | None:
    """Remove the expense with ``expense_id``; return it, or ``None`` if absent."""
    for index, entry in enumerate(expenses):
        if entry.get("id") == expense_id:
            return expenses.pop(index)
    return None


def filter_by_category(expenses: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    """Return all expenses belonging to ``category`` (case-insensitive)."""
    needle = category.strip().lower()
    return [entry for entry in expenses if str(entry.get("category", "")).lower() == needle]


# --------------------------------------------------------------------------- #
# Reporting (bonus: monthly summary with f-strings + aggregation)
# --------------------------------------------------------------------------- #
def monthly_summary(expenses: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group expenses by ``YYYY-MM`` month with totals and per-category stats.

    Returns a mapping::

        {
          "2026-10": {
              "total": 120.5,
              "count": 3,
              "categories": {
                  "food": {"total": 80.0, "count": 2, "average": 40.0},
                  ...
              },
          },
          ...
        }
    """
    summary: dict[str, dict[str, Any]] = {}

    for entry in expenses:
        date_str = str(entry.get("date", ""))
        if len(date_str) < 7:
            continue

        month = date_str[:7]
        category = str(entry.get("category", "unknown"))
        amount = float(entry.get("amount", 0.0))

        bucket = summary.setdefault(month, {"total": 0.0, "count": 0, "categories": {}})
        bucket["total"] += amount
        bucket["count"] += 1

        cat = bucket["categories"].setdefault(category, {"total": 0.0, "count": 0})
        cat["total"] += amount
        cat["count"] += 1

    for bucket in summary.values():
        for cat in bucket["categories"].values():
            cat["average"] = cat["total"] / cat["count"] if cat["count"] else 0.0

    return summary


def render_monthly_summary(expenses: list[dict[str, Any]]) -> str:
    """Build a printable monthly summary report."""
    summary = monthly_summary(expenses)
    if not summary:
        return "No expenses recorded yet - nothing to summarise."

    lines: list[str] = []
    for month in sorted(summary):
        bucket = summary[month]
        lines.append(f"\n{'=' * 52}")
        lines.append(f"Month: {month}")
        lines.append(f"Total spend: ${bucket['total']:.2f}  ({bucket['count']} expense(s))")
        lines.append(f"{'-' * 52}")
        lines.append(f"{'Category':<16}{'Total':>10}{'Count':>8}{'Average':>12}")

        for category in sorted(bucket["categories"]):
            cat = bucket["categories"][category]
            lines.append(
                f"{category:<16}"
                f"{cat['total']:>10.2f}"
                f"{cat['count']:>8}"
                f"{cat['average']:>12.2f}"
            )

        overall_average = bucket["total"] / bucket["count"] if bucket["count"] else 0.0
        lines.append(f"{'-' * 52}")
        lines.append(f"Average per expense: ${overall_average:.2f}")

    lines.append(f"\n{'=' * 52}")
    return "\n".join(lines)


def render_expense_table(expenses: list[dict[str, Any]]) -> str:
    """Build a printable table of raw expenses."""
    if not expenses:
        return "No expenses recorded yet."

    lines = [
        f"{'ID':<5}{'Date':<13}{'Category':<16}{'Amount':>10}",
        "-" * 44,
    ]
    for entry in sorted(expenses, key=lambda e: (str(e.get("date", "")), e.get("id", 0))):
        lines.append(
            f"{entry.get('id', '?'):<5}"
            f"{str(entry.get('date', '')):<13}"
            f"{str(entry.get('category', '')):<16}"
            f"{float(entry.get('amount', 0.0)):>10.2f}"
        )
    lines.append("-" * 44)
    lines.append(f"{'TOTAL':<34}{sum(float(e.get('amount', 0.0)) for e in expenses):>10.2f}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
MENU = """
============================================================
                EXPENSE TRACKER (JSON persistence)
============================================================
  1) Add expense
  2) View all expenses
  3) Monthly summary
  4) Filter by category
  5) Delete expense
  6) Show available categories
  0) Save & quit
============================================================"""


def prompt(message: str) -> str:
    """Read a line from the user (stripped)."""
    return input(message).strip()


def action_add(expenses: list[dict[str, Any]]) -> None:
    print("\n-- Add expense --")
    try:
        amount = parse_amount(prompt("Amount (e.g. 24.99): "))
    except ValueError as exc:
        print(f"[error] {exc}")
        return

    print(f"Suggested categories: {', '.join(DEFAULT_CATEGORIES)}")
    try:
        category = parse_category(prompt("Category: "))
    except ValueError as exc:
        print(f"[error] {exc}")
        return

    date_input = prompt("Date [YYYY-MM-DD] (blank = today): ")
    if not date_input:
        date_input = datetime.today().date().isoformat()
    try:
        date_str = parse_date(date_input)
    except ValueError as exc:
        print(f"[error] {exc}")
        return

    entry = add_expense(expenses, amount, category, date_str)
    print(f"[ok] Added expense #{entry['id']}: ${entry['amount']:.2f} in '{entry['category']}' on {entry['date']}.")


def action_view(expenses: list[dict[str, Any]]) -> None:
    print()
    print(render_expense_table(expenses))


def action_summary(expenses: list[dict[str, Any]]) -> None:
    print(render_monthly_summary(expenses))


def action_filter(expenses: list[dict[str, Any]]) -> None:
    category = prompt("Category to filter: ")
    if not category:
        print("[error] Category cannot be empty.")
        return
    matches = filter_by_category(expenses, category)
    print()
    print(render_expense_table(matches))


def action_delete(expenses: list[dict[str, Any]]) -> None:
    raw = prompt("Expense ID to delete: ")
    try:
        expense_id = int(raw)
    except ValueError:
        print("[error] ID must be an integer.")
        return

    removed = delete_expense(expenses, expense_id)
    if removed is None:
        print(f"[error] No expense with id {expense_id}.")
    else:
        print(f"[ok] Deleted expense #{expense_id} (${removed['amount']:.2f}, {removed['category']}).")


ACTIONS: dict[str, Any] = {
    "1": action_add,
    "2": action_view,
    "3": action_summary,
    "4": action_filter,
    "5": action_delete,
}


def run_cli() -> None:
    """Interactive main loop."""
    expenses = load_expenses()
    if expenses:
        print(f"Loaded {len(expenses)} expense(s) from {DATA_FILE.name}.")

    while True:
        print(MENU)
        choice = prompt("Choose an option: ")

        if choice == "0":
            save_expenses(expenses)
            print(f"\nSaved {len(expenses)} expense(s) to {DATA_FILE.name}. Goodbye!")
            return

        if choice == "6":
            print(f"\nDefault categories: {', '.join(DEFAULT_CATEGORIES)}")
            continue

        action = ACTIONS.get(choice)
        if action is None:
            print("[error] Unknown option. Please choose 0-6.")
            continue

        try:
            action(expenses)
        except KeyboardInterrupt:
            print("\n[cancelled]")

        # Persist after every mutation so data survives an unexpected exit.
        save_expenses(expenses)


def main() -> None:
    print("Expense Tracker - data file:", DATA_FILE)
    try:
        run_cli()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted. Your data was saved after the last change.")


if __name__ == "__main__":
    main()

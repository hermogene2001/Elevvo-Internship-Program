# Task 1 — CLI Expense Tracker with Persistent Storage

**Level 1 · Modules 1, 2 & 4 · Tools: `json`**

A command-line expense tracker that accepts user input for **amount**, **category**
and **date**, keeps entries in memory using **lists and dictionaries**, and
persists them to a local JSON file so data survives between runs and is reloaded
on startup.

**Covered topics:** Variables & Data Types · Lists & Dictionaries · File I/O · Basic CLI Design

**Bonus implemented:** monthly summary report using f-strings and basic
aggregation (total spend, count, and average per category).

## Files

| File | Purpose |
|------|---------|
| `expense_tracker.py` | The complete tracker (persistence, validation, CLI, reporting). |
| `expenses.json` | Created automatically on first save. |

## Run

```bash
cd task1_expense_tracker
python expense_tracker.py
```

## Menu

```
1) Add expense        4) Filter by category
2) View all expenses  5) Delete expense
3) Monthly summary    6) Show available categories
0) Save & quit
```

## Design notes

- **Persistence** — `load_expenses()` reads the JSON file on startup and
  `save_expenses()` writes it after every change, so nothing is lost if the
  program is interrupted.
- **Robust loading** — a missing, unreadable, malformed, or non-list JSON file
  degrades gracefully to an empty ledger with a warning instead of crashing.
- **Validation** — amounts must be positive numbers, dates must be valid
  `YYYY-MM-DD`, and categories cannot be blank.
- **Data shape** — each entry is a dictionary:
  ```json
  { "id": 1, "amount": 24.99, "category": "food", "date": "2026-10-19" }
  ```
- **Bonus summary** — groups expenses by `YYYY-MM`, reporting the monthly total,
  per-category total/count/average, and the overall average per expense.

## Example session

```
Amount (e.g. 24.99): 24.99
Category: food
Date [YYYY-MM-DD] (blank = today): 2026-10-19
[ok] Added expense #1: $24.99 in 'food' on 2026-10-19.
```

Selecting option `3` prints the monthly summary:

```
====================================================
Month: 2026-10
Total spend: $24.99  (1 expense(s))
----------------------------------------------------
Category             Total   Count     Average
food                 24.99       1       24.99
----------------------------------------------------
Average per expense: $24.99
====================================================
```

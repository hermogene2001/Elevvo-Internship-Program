# Task 2 — Student Grade Processor with Custom Functions

**Level 1 · Module 3 · Tools: Python (standard library only)**

A set of **modular functions** that calculate the average, highest/lowest score,
and pass/fail status for a list of student records. The logic lives in a
**separate importable module** (`grades.py`) rather than a single file.

**Covered topics:** Functions & Parameters · Modules & Imports · PEP 8 Style · Input Validation

**Bonus implemented:** a custom `InvalidScoreError` exception class for invalid
score input, plus full **type hints** on every public signature.

## Files

| File | Purpose |
|------|---------|
| `grades.py` | The importable module: records, validation, statistics, reporting. |
| `main.py` | Driver program that imports and uses the module. |
| `test_grades.py` | Unit tests (stdlib `unittest`, also runs under `pytest`). |

## Run

```bash
cd task2_grade_processor

# Interactive: enter students and scores yourself
python main.py

# Demo: run against a built-in sample class
python main.py --demo

# Tests
python -m unittest test_grades -v
# or:  pytest test_grades.py -v
```

## Module API (`grades.py`)

| Function | Returns |
|----------|---------|
| `validate_score(score)` | float, or raises `InvalidScoreError` |
| `validate_scores(scores)` | list of validated floats |
| `average(scores)` | arithmetic mean |
| `highest(scores)` / `lowest(scores)` | max / min |
| `pass_fail(avg, passing_score=50)` | `"PASS"` or `"FAIL"` |
| `summarize_student(record)` | `StudentReport` |
| `summarize_all(records)` | `list[StudentReport]` |
| `class_average(records)` | mean of all individual scores |
| `class_summary(records)` | dict of aggregate stats |
| `render_report(reports)` | formatted table string |

### Data types

- `StudentRecord(name: str, scores: list[float])` — accepts a plain
  `{"name": ..., "scores": [...]}` dict via `StudentRecord.from_mapping(...)`.
- `StudentReport` — the computed result; has `.passed`, `.as_dict()` and a
  readable `__str__`.

## Design notes

- **Separation of concerns** — `grades.py` never prints; `main.py` owns all I/O,
  which makes the logic reusable and testable.
- **Input validation** — scores outside `0–100`, non-numeric values (including
  `bool`), empty score lists, and blank student names are all rejected.
- **Errors are meaningful** — `InvalidScoreError` subclasses `ValueError` and
  carries the offending value, so callers can catch either the specific or the
  general exception.
- **PEP 8** — module docstring, snake_case, typed signatures, `from __future__
  import annotations`, and consistent formatting.

## Example (`python main.py --demo`)

```
Student            Scores   Average  Highest   Lowest  Status
--------------------------------------------------------------
Amara                   4     88.50    95.00    79.00    PASS
Bekele                  4     49.00    61.00    38.00    FAIL
Chidi                   3     96.33   100.00    91.00    PASS
Desta                   4     68.75    72.00    65.00    PASS
Fatima                  3     42.00    55.00    30.00    FAIL

====================================================
Students:       5
Passed:         3
Failed:         2
Pass rate:      60.0%
Class average:  68.92
Top student:    Chidi
====================================================
```

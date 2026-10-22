#!/usr/bin/env python3
"""Task 2 - Student Grade Processor (importable module).

Modular, importable functions that compute the average, highest/lowest score
and pass/fail status for student records.

The module is deliberately free of any CLI/printing concerns so it can be
imported and reused by ``main.py``, tests, or any other program.

Covered topics:
    Functions & Parameters | Modules & Imports | PEP 8 Style | Input Validation

Bonus:
    - Custom ``InvalidScoreError`` exception for bad score input.
    - Full type hints on every public function signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
MIN_SCORE: float = 0.0
MAX_SCORE: float = 100.0
PASSING_SCORE: float = 50.0

PASS: str = "PASS"
FAIL: str = "FAIL"


# --------------------------------------------------------------------------- #
# Custom exception (bonus)
# --------------------------------------------------------------------------- #
class InvalidScoreError(ValueError):
    """Raised when a score is not numeric or falls outside 0-100."""

    def __init__(self, score: Any, message: str | None = None) -> None:
        self.score = score
        detail = message or (
            f"Invalid score {score!r}: expected a number between "
            f"{MIN_SCORE:g} and {MAX_SCORE:g}."
        )
        super().__init__(detail)


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #
@dataclass
class StudentRecord:
    """A single student and the scores they achieved."""

    name: str
    scores: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("Student name cannot be empty.")

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StudentRecord":
        """Build a record from a plain ``{"name": ..., "scores": [...]}`` dict."""
        if "name" not in data:
            raise ValueError("Record is missing a 'name' key.")
        return cls(name=data["name"], scores=list(data.get("scores", [])))


@dataclass
class StudentReport:
    """The computed result for one student."""

    name: str
    count: int
    average: float
    highest: float
    lowest: float
    status: str  # "PASS" or "FAIL"

    @property
    def passed(self) -> bool:
        return self.status == PASS

    def as_dict(self) -> dict[str, Any]:
        """Return the report as a plain dictionary (JSON-friendly)."""
        return {
            "name": self.name,
            "count": self.count,
            "average": round(self.average, 2),
            "highest": self.highest,
            "lowest": self.lowest,
            "status": self.status,
        }

    def __str__(self) -> str:
        return (
            f"{self.name:<18}"
            f"{self.count:>6}"
            f"{self.average:>10.2f}"
            f"{self.highest:>9.2f}"
            f"{self.lowest:>9.2f}"
            f"{self.status:>8}"
        )


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_score(score: Any) -> float:
    """Return ``score`` as a float after validating it is within range.

    Raises:
        InvalidScoreError: if the value is not numeric or outside 0-100.
    """
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise InvalidScoreError(score, f"Score must be numeric, got {type(score).__name__} ({score!r}).")

    value = float(score)
    if value < MIN_SCORE or value > MAX_SCORE:
        raise InvalidScoreError(value)

    return value


def validate_scores(scores: Iterable[Any]) -> list[float]:
    """Validate every score in ``scores`` and return a list of floats."""
    return [validate_score(score) for score in scores]


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def _require_scores(scores: Sequence[float]) -> list[float]:
    """Validate and return scores, rejecting an empty collection."""
    if not scores:
        raise ValueError("Cannot compute statistics for an empty list of scores.")
    return [validate_score(score) for score in scores]


def average(scores: Sequence[float]) -> float:
    """Return the arithmetic mean of ``scores``."""
    values = _require_scores(scores)
    return sum(values) / len(values)


def highest(scores: Sequence[float]) -> float:
    """Return the highest score."""
    return max(_require_scores(scores))


def lowest(scores: Sequence[float]) -> float:
    """Return the lowest score."""
    return min(_require_scores(scores))


def pass_fail(average_score: float, passing_score: float = PASSING_SCORE) -> str:
    """Return ``"PASS"`` or ``"FAIL"`` for an average against ``passing_score``."""
    checked = validate_score(average_score)
    return PASS if checked >= passing_score else FAIL


# --------------------------------------------------------------------------- #
# High-level processing
# --------------------------------------------------------------------------- #
def summarize_student(
    record: StudentRecord | dict[str, Any],
    passing_score: float = PASSING_SCORE,
) -> StudentReport:
    """Compute a :class:`StudentReport` for one student."""
    if isinstance(record, dict):
        record = StudentRecord.from_mapping(record)

    values = _require_scores(record.scores)
    avg = sum(values) / len(values)

    return StudentReport(
        name=record.name,
        count=len(values),
        average=avg,
        highest=max(values),
        lowest=min(values),
        status=pass_fail(avg, passing_score),
    )


def summarize_all(
    records: Iterable[StudentRecord | dict[str, Any]],
    passing_score: float = PASSING_SCORE,
) -> list[StudentReport]:
    """Compute reports for a collection of student records."""
    return [summarize_student(record, passing_score) for record in records]


def class_average(records: Iterable[StudentRecord | dict[str, Any]]) -> float:
    """Return the mean of every individual score across all students."""
    all_scores: list[float] = []
    for record in records:
        values = record.scores if isinstance(record, StudentRecord) else record.get("scores", [])
        all_scores.extend(validate_score(score) for score in values)

    if not all_scores:
        raise ValueError("No scores available to compute a class average.")

    return sum(all_scores) / len(all_scores)


def class_summary(
    records: Iterable[StudentRecord | dict[str, Any]],
    passing_score: float = PASSING_SCORE,
) -> dict[str, Any]:
    """Return an aggregate summary across all students."""
    reports = summarize_all(records, passing_score)

    if not reports:
        return {
            "students": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "class_average": 0.0,
            "top_student": None,
        }

    passed = sum(1 for report in reports if report.passed)
    top = max(reports, key=lambda report: report.average)

    return {
        "students": len(reports),
        "passed": passed,
        "failed": len(reports) - passed,
        "pass_rate": (passed / len(reports)) * 100,
        "class_average": sum(report.average for report in reports) / len(reports),
        "top_student": top.name,
    }


def render_report(reports: Sequence[StudentReport]) -> str:
    """Return a formatted table of student reports (uses f-strings)."""
    if not reports:
        return "No student records to report."

    header = (
        f"{'Student':<18}{'Scores':>6}{'Average':>10}{'Highest':>9}{'Lowest':>9}{'Status':>8}"
    )
    lines = [header, "-" * len(header)]
    lines.extend(str(report) for report in reports)
    return "\n".join(lines)

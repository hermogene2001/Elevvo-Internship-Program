#!/usr/bin/env python3
"""Tests for the ``grades`` module.

Run with either::

    python -m unittest test_grades -v
    pytest test_grades.py -v
"""

from __future__ import annotations

import unittest

from grades import (
    FAIL,
    PASS,
    InvalidScoreError,
    StudentRecord,
    average,
    class_summary,
    highest,
    lowest,
    pass_fail,
    summarize_all,
    summarize_student,
    validate_score,
    validate_scores,
)


class TestValidation(unittest.TestCase):
    def test_accepts_valid_scores(self) -> None:
        self.assertEqual(validate_score(0), 0.0)
        self.assertEqual(validate_score(100), 100.0)
        self.assertEqual(validate_score(87.5), 87.5)

    def test_rejects_negative(self) -> None:
        with self.assertRaises(InvalidScoreError):
            validate_score(-1)

    def test_rejects_above_hundred(self) -> None:
        with self.assertRaises(InvalidScoreError):
            validate_score(101)

    def test_rejects_non_numeric(self) -> None:
        for bad in ("ninety", None, [90], True):
            with self.assertRaises(InvalidScoreError):
                validate_score(bad)

    def test_validate_scores_lists(self) -> None:
        self.assertEqual(validate_scores([10, 20, 30]), [10.0, 20.0, 30.0])


class TestStatistics(unittest.TestCase):
    def test_average(self) -> None:
        self.assertAlmostEqual(average([80, 90, 100]), 90.0)

    def test_highest_lowest(self) -> None:
        self.assertEqual(highest([55, 99, 71]), 99)
        self.assertEqual(lowest([55, 99, 71]), 55)

    def test_empty_raises(self) -> None:
        for func in (average, highest, lowest):
            with self.assertRaises(ValueError):
                func([])

    def test_pass_fail(self) -> None:
        self.assertEqual(pass_fail(50), PASS)
        self.assertEqual(pass_fail(49.9), FAIL)

    def test_propagates_invalid_scores(self) -> None:
        with self.assertRaises(InvalidScoreError):
            average([80, -5])


class TestSummaries(unittest.TestCase):
    def test_summarize_student_pass(self) -> None:
        report = summarize_student({"name": "Amara", "scores": [90, 80, 100]})
        self.assertEqual(report.name, "Amara")
        self.assertEqual(report.count, 3)
        self.assertAlmostEqual(report.average, 90.0)
        self.assertEqual(report.highest, 100)
        self.assertEqual(report.lowest, 80)
        self.assertEqual(report.status, PASS)
        self.assertTrue(report.passed)

    def test_summarize_student_fail(self) -> None:
        report = summarize_student(StudentRecord("Bekele", [40, 45, 30]))
        self.assertEqual(report.status, FAIL)
        self.assertFalse(report.passed)

    def test_as_dict(self) -> None:
        report = summarize_student({"name": "Chidi", "scores": [70, 71]})
        self.assertEqual(
            report.as_dict(),
            {"name": "Chidi", "count": 2, "average": 70.5, "highest": 71, "lowest": 70, "status": PASS},
        )

    def test_summarize_all(self) -> None:
        records = [
            {"name": "Amara", "scores": [90, 90]},
            {"name": "Bekele", "scores": [10, 20]},
        ]
        reports = summarize_all(records)
        self.assertEqual([r.status for r in reports], [PASS, FAIL])

    def test_class_summary(self) -> None:
        records = [
            {"name": "Amara", "scores": [90, 90]},
            {"name": "Bekele", "scores": [10, 20]},
            {"name": "Chidi", "scores": [70, 70]},
        ]
        summary = class_summary(records)
        self.assertEqual(summary["students"], 3)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["top_student"], "Amara")
        self.assertAlmostEqual(summary["pass_rate"], 200 / 3)

    def test_empty_record_rejected(self) -> None:
        with self.assertRaises(ValueError):
            summarize_student({"name": "Nobody", "scores": []})

    def test_blank_name_rejected(self) -> None:
        with self.assertRaises(ValueError):
            StudentRecord("   ", [50])


if __name__ == "__main__":
    unittest.main(verbosity=2)

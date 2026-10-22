#!/usr/bin/env python3
"""Tests for Task 8 (Code Review Tool)."""

from __future__ import annotations

import unittest

from code_review import CodeReviewTool, parse_and_validate, validate_issue


class TestValidation(unittest.TestCase):
    def test_valid_issue_accepted(self) -> None:
        issue, disc = validate_issue(
            {"issue": "Bad variable name", "line": 5, "suggestion": "Use snake_case"},
            ["a"] * 10,
        )
        self.assertIsNotNone(issue)
        self.assertIsNone(disc)
        self.assertTrue(issue.verified)

    def test_missing_field_discarded(self) -> None:
        issue, disc = validate_issue(
            {"issue": "Problem", "suggestion": "Fix it"},  # missing line
            ["a"] * 10,
        )
        self.assertIsNone(issue)
        self.assertIsNotNone(disc)
        self.assertIn("missing", disc["reason"])

    def test_empty_field_discarded(self) -> None:
        issue, disc = validate_issue(
            {"issue": "", "line": 1, "suggestion": "Fix"},
            ["a"] * 10,
        )
        self.assertIsNone(issue)
        self.assertIsNotNone(disc)

    def test_line_out_of_range_marked_approximate(self) -> None:
        issue, _ = validate_issue(
            {"issue": "Problem", "line": 999, "suggestion": "Fix"},
            ["a"] * 10,
        )
        self.assertEqual(issue.line, "approximate")
        self.assertFalse(issue.verified)

    def test_approximate_line_preserved(self) -> None:
        issue, _ = validate_issue(
            {"issue": "Problem", "line": "approximate", "suggestion": "Fix"},
            ["a"] * 10,
        )
        self.assertEqual(issue.line, "approximate")

    def test_invalid_json_discarded(self) -> None:
        valid, discarded, total = parse_and_validate("not json", ["a"] * 5)
        self.assertEqual(valid, [])
        self.assertEqual(total, 0)
        self.assertTrue(len(discarded) > 0)

    def test_mixed_valid_invalid(self) -> None:
        response = '{"issues": [{"issue": "ok", "line": 1, "suggestion": "do it"}, {"issue": "", "line": 2, "suggestion": "x"}]}'
        valid, discarded, total = parse_and_validate(response, ["a"] * 10)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(discarded), 1)
        self.assertEqual(total, 2)


class TestCodeReviewTool(unittest.TestCase):
    def test_demo_does_not_apply_changes(self) -> None:
        tool = CodeReviewTool(use_openai=False)
        report = tool.review_code("x = 1", "test.py")
        self.assertIsInstance(report.issues, list)
        # Demo mode discards bad entries
        self.assertEqual(report.total_raw, 5)
        self.assertTrue(report.total_valid < report.total_raw)

    def test_report_format(self) -> None:
        tool = CodeReviewTool(use_openai=False)
        report = tool.review_code("x = 1", "test.py")
        formatted = tool.format_report(report)
        self.assertIn("CODE REVIEW REPORT", formatted)
        self.assertIn("reports suggestions only", formatted)


if __name__ == "__main__":
    unittest.main(verbosity=2)

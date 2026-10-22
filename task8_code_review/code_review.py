#!/usr/bin/env python3
"""Task 8 - AI-Assisted Code Review Tool.

Takes a Python file and sends it to an LLM with a structured prompt asking for
bug detection, PEP 8 compliance review, and refactor suggestions. Parses the
LLM's response into a structured report (JSON with issue, line, suggestion
fields). Validates each entry contains all required fields with valid,
non-empty values - discards or flags entries that fail validation. Line
numbers may be marked "approximate" when unverifiable against the actual file.
This tool reviews and reports suggestions only - it must never automatically
execute or apply AI-generated code changes.

Covered topics:
    AI-Assisted Development | Prompt Engineering for Structured Output |
    Code Quality Review | Output Validation
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class ReviewIssue:
    issue: str
    line: int | str  # int if verifiable, "approximate" or string if not
    suggestion: str
    category: str = "general"  # bug | pep8 | refactor | general
    severity: str = "medium"
    valid: bool = True
    verified: bool = False


@dataclass
class ReviewReport:
    filename: str
    issues: list[ReviewIssue]
    discarded: list[dict[str, Any]]
    total_raw: int
    total_valid: int


# --------------------------------------------------------------------------- #
# Prompting (structured output)
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = """You are an expert Python code reviewer. 
Review the provided Python file for:
1. Bugs and potential errors
2. PEP 8 compliance issues  
3. Refactoring suggestions for better code quality

You MUST respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "issue": "Clear description of the problem",
      "line": <number or "approximate">,
      "suggestion": "Specific actionable suggestion",
      "category": "bug|pep8|refactor|general",
      "severity": "low|medium|high"
    }
  ]
}

Rules:
- Each issue MUST have non-empty "issue", "line", "suggestion" fields
- If you are not certain about the exact line number, use "approximate"
- Be specific and actionable
- Only report real issues, don't nitpick excessively
- Do NOT suggest executing or applying changes automatically
"""


def build_user_prompt(code: str, filename: str) -> str:
    return f"Review this Python file: {filename}\n\n```python\n{code}\n```"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
REQUIRED_FIELDS = ("issue", "line", "suggestion")


def validate_issue(raw: Any, source_lines: list[str]) -> tuple[ReviewIssue | None, dict[str, Any] | None]:
    """Validate a single issue entry. Returns (valid_issue, discarded_info)."""
    if not isinstance(raw, dict):
        return None, {"raw": raw, "reason": "not a dictionary"}

    # Check required fields exist and are non-empty
    for field in REQUIRED_FIELDS:
        if field not in raw:
            return None, {"raw": raw, "reason": f"missing required field '{field}'"}
        val = raw[field]
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return None, {"raw": raw, "reason": f"field '{field}' is empty or null"}

    issue_text = str(raw["issue"]).strip()
    suggestion_text = str(raw["suggestion"]).strip()
    line_val = raw["line"]

    # Validate line
    verified = False
    if isinstance(line_val, int):
        if 1 <= line_val <= len(source_lines):
            verified = True
        else:
            line_val = "approximate"
    elif isinstance(line_val, str):
        if line_val.strip().lower() == "approximate":
            line_val = "approximate"
        else:
            # Try to parse as int
            try:
                num = int(line_val.strip())
                if 1 <= num <= len(source_lines):
                    line_val = num
                    verified = True
                else:
                    line_val = "approximate"
            except ValueError:
                line_val = "approximate"
    else:
        return None, {"raw": raw, "reason": "line must be int or string"}

    category = str(raw.get("category", "general")).strip().lower()
    if category not in ("bug", "pep8", "refactor", "general"):
        category = "general"

    severity = str(raw.get("severity", "medium")).strip().lower()
    if severity not in ("low", "medium", "high"):
        severity = "medium"

    return ReviewIssue(
        issue=issue_text,
        line=line_val,
        suggestion=suggestion_text,
        category=category,
        severity=severity,
        valid=True,
        verified=verified,
    ), None


def parse_and_validate(response_text: str, source_lines: list[str]) -> tuple[list[ReviewIssue], list[dict[str, Any]], int]:
    """Parse JSON response and validate each entry."""
    discarded: list[dict[str, Any]] = []

    # Try to extract JSON from response (in case of markdown code blocks)
    text = response_text.strip()
    if "```json" in text:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    elif "```" in text:
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        discarded.append({"raw_response": response_text[:500], "reason": f"Invalid JSON: {exc}"})
        return [], discarded, 0

    if not isinstance(data, dict) or "issues" not in data:
        discarded.append({"raw": data, "reason": "Response missing 'issues' array"})
        return [], discarded, 0

    issues_raw = data["issues"]
    if not isinstance(issues_raw, list):
        discarded.append({"raw": issues_raw, "reason": "'issues' is not a list"})
        return [], discarded, 0

    valid_issues: list[ReviewIssue] = []
    for entry in issues_raw:
        valid, disc = validate_issue(entry, source_lines)
        if valid is not None:
            valid_issues.append(valid)
        elif disc is not None:
            discarded.append(disc)

    return valid_issues, discarded, len(issues_raw)


# --------------------------------------------------------------------------- #
# Review
# --------------------------------------------------------------------------- #
class CodeReviewTool:
    def __init__(self, use_openai: bool = False, model: str = "gpt-4o-mini"):
        self.use_openai = use_openai
        self.model = model
        if use_openai:
            if OpenAI is None:
                raise RuntimeError("openai package not installed")
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.client = None

    def review_file(self, filepath: Path) -> ReviewReport:
        code = filepath.read_text(encoding="utf-8")
        source_lines = code.splitlines()
        return self.review_code(code, filepath.name, source_lines)

    def review_code(self, code: str, filename: str = "<string>", source_lines: list[str] | None = None) -> ReviewReport:
        if source_lines is None:
            source_lines = code.splitlines()

        if self.use_openai and self.client is not None:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_user_prompt(code, filename)},
                    ],
                    temperature=0,
                )
                response_text = resp.choices[0].message.content
            except Exception as exc:
                response_text = json.dumps({"issues": [{"issue": f"API error: {exc}", "line": "approximate", "suggestion": "Check API key and connection", "category": "general", "severity": "high"}]})
        else:
            # Demo response (no API key) - shows validation in action
            response_text = json.dumps({
                "issues": [
                    {"issue": "Missing docstring for module", "line": 1, "suggestion": "Add a module-level docstring explaining purpose", "category": "pep8", "severity": "low"},
                    {"issue": "Possible division by zero", "line": 999, "suggestion": "Add check before division", "category": "bug", "severity": "high"},
                    {"issue": "Could use list comprehension", "line": 5, "suggestine": "Use list comprehension for clarity", "category": "refactor", "severity": "medium"},  # typo in field
                    {"line": 10, "suggestion": "Fix this", "category": "bug", "severity": "high"},  # missing issue
                    {"issue": "", "line": 15, "suggestion": "Something", "category": "pep8", "severity": "low"},  # empty issue
                ]
            })

        valid_issues, discarded, total_raw = parse_and_validate(response_text, source_lines)

        return ReviewReport(
            filename=filename,
            issues=valid_issues,
            discarded=discarded,
            total_raw=total_raw,
            total_valid=len(valid_issues),
        )

    def format_report(self, report: ReviewReport) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append(f"CODE REVIEW REPORT - {report.filename}")
        lines.append("=" * 70)
        lines.append(f"Total issues found: {report.total_raw} | Valid: {report.total_valid} | Discarded: {len(report.discarded)}")
        lines.append("")
        lines.append("IMPORTANT: This tool reports suggestions only. No changes have been applied.")
        lines.append("=" * 70)
        lines.append("")

        if not report.issues:
            lines.append("No valid issues found.")
        else:
            for i, issue in enumerate(report.issues, 1):
                verified_str = "✓ verified" if issue.verified else "⚠ approximate/unverified"
                lines.append(f"[{i}] {issue.category.upper()} - {issue.severity.upper()} ({verified_str})")
                lines.append(f"    Line: {issue.line}")
                lines.append(f"    Issue: {issue.issue}")
                lines.append(f"    Suggestion: {issue.suggestion}")
                lines.append("")

        if report.discarded:
            lines.append("-" * 70)
            lines.append(f"DISCARDED ENTRIES ({len(report.discarded)})")
            lines.append("-" * 70)
            for i, d in enumerate(report.discarded, 1):
                lines.append(f"  [{i}] {d.get('reason', 'validation failed')}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


def main() -> None:
    import sys
    tool = CodeReviewTool(use_openai=False)
    
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            return
        report = tool.review_file(filepath)
    else:
        # Demo with a sample file
        sample_code = '''def calculate(x,y):
    return x/y

def process_items(items=[]):
    result = []
    for i in range(len(items)):
        result.append(items[i]*2)
    return result
'''
        report = tool.review_code(sample_code, "sample.py")
    
    print(tool.format_report(report))


if __name__ == "__main__":
    main()

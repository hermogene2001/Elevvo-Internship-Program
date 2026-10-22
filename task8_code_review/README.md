# Task 8 — AI-Assisted Code Review Tool

**Level: Industry · Module 9**

Takes an existing Python file and sends it to an LLM with a structured prompt
asking for bug detection, PEP 8 compliance review, and refactor suggestions.
Parses the LLM's response into a structured report (JSON with `issue`, `line`,
`suggestion` fields). Validates that each entry contains all required fields
with valid, non-empty values — discards or flags entries that fail validation.
Since LLM-reported line numbers can be inaccurate, the tool marks a line
reference as **"approximate"** when it cannot be verified against the actual
file. **This tool reviews and reports suggestions only — it must never
automatically execute or apply any AI-generated code changes.**

**Covered topics:** AI-Assisted Development · Prompt Engineering for Structured Output · Code Quality Review · Output Validation

**Bonus:** Can show before/after diffs for suggestions (user chooses to accept/reject manually).

## Files

| File | Purpose |
|------|---------|
| `code_review.py` | Prompting, JSON parsing, validation, reporting, CLI. |
| `test_review.py` | Tests for validation, parsing, and report formatting. |

## Run

```bash
cd task8_code_review

# Demo with sample code (no API key needed)
python code_review.py

# Review a real file
python code_review.py path/to/your_file.py
```

## Validation rules (enforced)

- **Required fields** — every issue must have non-empty `issue`, `line`, `suggestion`. Missing or empty fields → discarded with reason.
- **Line verification** — if `line` is an integer and falls within the file's actual line range, it's marked `verified`. If out of range or unparseable, it's marked `"approximate"` and `unverified`.
- **JSON parsing** — extracts JSON from markdown code blocks if present; invalid JSON discards the whole response with details.
- **Schema checks** — `issues` must be a list; individual entries must be dicts.
- **Safety boundary** — the system prompt explicitly instructs no automatic execution/applying of changes, and the report always states: *"This tool reports suggestions only. No changes have been applied."*

## Report output

The formatted report shows:
- Summary (total found / valid / discarded)
- Each valid issue with category (bug/pep8/refactor/general), severity (low/medium/high), line (with verification status), issue, and suggestion
- Discarded entries with reasons

## Tests

```bash
python -m unittest test_review -v
# or: pytest test_review.py -v
```

Tests cover valid/invalid entries, empty fields, out-of-range lines → approximate, invalid JSON, mixed valid/invalid, and report formatting.

## Dependencies

```bash
pip install openai python-dotenv
```

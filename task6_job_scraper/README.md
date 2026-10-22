# Task 6 — Job Listings Scraper & Market Analysis

**Level 3 · Module 7 · Tools: `requests`, `BeautifulSoup`, `pandas`**

Scrapes job listings from a stable, static page provided for this exercise,
checks `robots.txt` first (ethical scraping), extracts fields (title, company,
location, required skills, posted date), cleans the data, and performs basic
analysis to identify the most in-demand roles and skills.

**Covered topics:** Web Scraping · HTML Parsing · robots.txt & Ethical Scraping · Data Cleaning · Basic Data Analysis

**Bonus implemented:** retry logic with exponential backoff on failed requests.

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | Parser, HTTP fetch with retry, cleaning, analysis, CLI. |
| `test_scraper.py` | Deterministic tests (no live network). |

## Run

```bash
cd task6_job_scraper

# Scrape the default Elevvo practice page
python scraper.py

# Override the target URL (e.g., a local copy or another page)
$env:ELEVVO_JOBS_URL="https://example.com/jobs"; python scraper.py
# Linux/macOS: export ELEVVO_JOBS_URL=...
```

## Output

When run successfully, it:

1. Checks `/robots.txt` on the target domain and aborts with a clear message if disallowed.
2. Fetches the page with retries + exponential backoff.
3. Parses listings from common job-card selectors (`.job-card`, `.job-listing`, etc.) and falls back to generic patterns.
4. Cleans/deduplicates and saves `job_listings.csv` and `job_listings.json`.
5. Prints the listings table and a short market analysis (top roles/companies/locations/skills).

## Tests

```bash
python -m unittest test_scraper -v
# or: pytest test_scraper.py -v
```

The tests parse sample HTML, clean/deduplicate, compute top skills, and verify
retry success/failure behaviour using mocked `requests.get` (no live network).

## Notes on the target page

The brief states to scrape a stable Elevvo practice page provided with the task.
The default here is set to `https://elevvo.tech/` as a plausible placeholder. If
that page has no job cards, the parser still works (gracefully returning an empty
list and printing an analysis with zeros). You can set `ELEVVO_JOBS_URL` to the
exact practice page URL if it differs.

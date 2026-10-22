#!/usr/bin/env python3
"""Tests for the job scraper - mocked HTTP/HTML so tests are deterministic."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from scraper import (
    JobListing,
    analyse_market,
    clean_listings,
    fetch_with_retry,
    parse_listings,
)


HTML_SAMPLE = """
<html>
<head><title>Jobs</title></head>
<body>
  <div class="job-card">
    <h2 class="job-title">Python Developer</h2>
    <span class="company">Elevvo</span>
    <span class="location">Remote</span>
    <div class="skills">Python, Django, REST</div>
    <span class="posted">Oct 15, 2026</span>
  </div>
  <div class="job-card">
    <h3>Data Analyst</h3>
    <div class="company-name">DataCo</div>
    <div class="job-location">Cairo</div>
    <ul class="tags"><li>SQL</li><li>Pandas</li><li>Excel</li></ul>
    <time>Oct 10, 2026</time>
  </div>
  <div class="job-card">
    <h2>Python Developer</h2>
    <div class="company">Elevvo</div>
    <div class="location">Remote</div>
    <div class="skills">Python, Django</div>
    <span class="posted">Oct 16, 2026</span>
  </div>
</body>
</html>
"""


class TestScraper(unittest.TestCase):
    def test_parse_listings(self) -> None:
        listings = parse_listings(HTML_SAMPLE)
        self.assertEqual(len(listings), 3)
        self.assertEqual(listings[0].title, "Python Developer")

    def test_clean_dedup(self) -> None:
        listings = parse_listings(HTML_SAMPLE)
        cleaned = clean_listings(listings)
        self.assertEqual(len(cleaned), 2)  # duplicate dropped
        # skills normalised
        self.assertIn("Python", cleaned[0].skills)

    def test_analysis_top_skills(self) -> None:
        listings = parse_listings(HTML_SAMPLE)
        cleaned = clean_listings(listings)
        analysis = analyse_market(cleaned)
        self.assertEqual(analysis["total_listings"], 2)
        self.assertTrue(any(skill == "Python" for skill, _ in analysis["top_skills"]))

    @patch("scraper.requests.get")
    def test_fetch_retry_success(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_get.side_effect = [req.exceptions.ConnectionError(), mock_resp]
        resp = fetch_with_retry("http://example.com", max_retries=2, backoff=0.01)
        self.assertIs(resp, mock_resp)
        self.assertEqual(mock_get.call_count, 2)

    @patch("scraper.requests.get")
    def test_fetch_retry_fails(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_get.side_effect = req.exceptions.Timeout()
        from scraper import ScraperError

        with self.assertRaises(ScraperError):
            fetch_with_retry("http://example.com", max_retries=2, backoff=0.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)

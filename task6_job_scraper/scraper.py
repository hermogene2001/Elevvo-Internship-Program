#!/usr/bin/env python3
"""Task 6 - Job Listings Scraper & Market Analysis.

Scrapes job listings from the Elevvo practice page provided for this task (a
stable, static page built specifically for this exercise). Checks robots.txt
first as a habit. Extracts job title, company, location, required skills and
posted date, cleans the data, and performs basic analysis to identify the
most in-demand roles/skills.

Covered topics:
    Web Scraping | HTML Parsing | robots.txt & Ethical Scraping | Data Cleaning |
    Basic Data Analysis

Bonus:
    Retry logic with exponential backoff for failed requests (see retry helpers).
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

# The stable Elevvo practice page for this exercise.
# If the URL changes, set ELEVVO_JOBS_URL in the environment.
DEFAULT_URL = "https://elevvo.tech/"

HEADERS = {
    "User-Agent": "Elevvo-Internship-Scraper/1.0 (educational exercise)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ScraperError(Exception):
    """Base scraper error."""


class RobotsBlockedError(ScraperError):
    """Raised when robots.txt disallows scraping this path."""


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    skills: list[str]
    posted_date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Ethics / robots.txt
# --------------------------------------------------------------------------- #
def check_robots(url: str, user_agent: str = HEADERS["User-Agent"]) -> bool:
    """Return True if allowed by robots.txt, False if disallowed."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # If robots.txt cannot be read, be conservative and report that we checked.
        return True

    return rp.can_fetch(user_agent, url)


def ensure_allowed(url: str, user_agent: str = HEADERS["User-Agent"]) -> None:
    """Raise if robots.txt explicitly disallows this URL."""
    if not check_robots(url, user_agent):
        raise RobotsBlockedError(
            f"Scraping disallowed by {urlparse(url).netloc}/robots.txt for user-agent '{user_agent}'"
        )


# --------------------------------------------------------------------------- #
# HTTP with retry + exponential backoff
# --------------------------------------------------------------------------- #
def fetch_with_retry(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    max_retries: int = 3,
    backoff: float = 0.5,
) -> requests.Response:
    """Fetch a URL with retries on transient failures."""
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers or HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt == max_retries:
                break
            time.sleep(backoff * (2 ** (attempt - 1)))
            continue

    raise ScraperError(f"Failed to fetch {url} after {max_retries} attempts: {last_exc}")


# --------------------------------------------------------------------------- #
# Parsing (works against common job-card patterns; falls back gracefully)
# --------------------------------------------------------------------------- #
def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _parse_skills(tag) -> list[str]:
    """Extract skills from common patterns (badges, tags, lists)."""
    skills: list[str] = []

    if tag is None:
        return skills

    for item in tag.select(".skill, .tag, .badge, .chip, li"):
        skills.append(_clean_text(item.get_text()))

    if not skills:
        text = _clean_text(tag.get_text())
        if "," in text:
            skills = [_clean_text(part) for part in text.split(",") if _clean_text(part)]

    return [s for s in skills if s]


def parse_listings(html: str) -> list[JobListing]:
    """Parse job cards from HTML into JobListing objects."""
    soup = BeautifulSoup(html, "html.parser")
    listings: list[JobListing] = []

    # Try multiple selectors so it works across slight page variations
    cards = (
        soup.select(".job-card, .job-listing, .listing-card, .vacancy-card, article.job")
        or soup.select("[data-job]")
        or soup.select("div.card")
    )

    for card in cards:
        title_el = (
            card.select_one(".job-title, .title, h2, h3")
            or card.find("a", class_=lambda c: c and "title" in c.lower())
        )
        company_el = card.select_one(".company, .company-name, .employer")
        location_el = card.select_one(".location, .job-location, .place")
        date_el = card.select_one(".date, .posted, .posted-date, time")
        skills_el = card.select_one(".skills, .tags, .requirements, ul")

        title = _clean_text(title_el.get_text()) if title_el else ""
        company = _clean_text(company_el.get_text()) if company_el else ""
        location = _clean_text(location_el.get_text()) if location_el else ""
        posted_date = _clean_text(date_el.get_text()) if date_el else ""
        skills = _parse_skills(skills_el)

        # If we can at least get a title, keep the card
        if title:
            listings.append(
                JobListing(
                    title=title,
                    company=company or "N/A",
                    location=location or "N/A",
                    skills=skills,
                    posted_date=posted_date or "N/A",
                )
            )

    return listings


# --------------------------------------------------------------------------- #
# Cleaning & Analysis
# --------------------------------------------------------------------------- #
def clean_listings(listings: list[JobListing]) -> list[JobListing]:
    """Normalise and de-duplicate listings."""
    seen: set[tuple[str, str, str]] = set()
    cleaned: list[JobListing] = []

    for job in listings:
        key = (
            job.title.strip().lower(),
            job.company.strip().lower(),
            job.location.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)

        skills = sorted({s.strip() for s in job.skills if s.strip()})
        cleaned.append(
            JobListing(
                title=_clean_text(job.title),
                company=_clean_text(job.company),
                location=_clean_text(job.location),
                skills=skills,
                posted_date=_clean_text(job.posted_date),
            )
        )

    return cleaned


def to_dataframe(listings: list[JobListing]) -> pd.DataFrame:
    return pd.DataFrame([job.to_dict() for job in listings])


def analyse_market(listings: list[JobListing]) -> dict[str, Any]:
    """Return basic market analysis: top roles, top skills, locations."""
    titles = Counter(job.title for job in listings)
    companies = Counter(job.company for job in listings)
    locations = Counter(job.location for job in listings)
    skills: Counter[str] = Counter()
    for job in listings:
        skills.update(job.skills)

    return {
        "total_listings": len(listings),
        "top_roles": titles.most_common(10),
        "top_companies": companies.most_common(10),
        "top_locations": locations.most_common(10),
        "top_skills": skills.most_common(15),
    }


def print_analysis(analysis: dict[str, Any]) -> None:
    print("=" * 60)
    print("MARKET ANALYSIS")
    print("=" * 60)
    print(f"Total listings: {analysis['total_listings']}")
    print()

    def section(name: str, items: list[tuple[str, int]]) -> None:
        if not items:
            print(f"{name}: (none)")
            print()
            return
        print(f"{name}:")
        for value, count in items:
            print(f"  {count:>3}x  {value}")
        print()

    section("Top roles", analysis["top_roles"])
    section("Top companies", analysis["top_companies"])
    section("Top locations", analysis["top_locations"])
    section("Top skills (in-demand)", analysis["top_skills"])


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def run_scraper(url: str = DEFAULT_URL, output: str | None = None) -> list[JobListing]:
    print(f"Checking robots.txt for {url}...")
    ensure_allowed(url)
    print("robots.txt: allowed")

    print(f"Fetching {url}...")
    resp = fetch_with_retry(url)
    print(f"Status: {resp.status_code} | Content length: {len(resp.text)}")

    print("Parsing listings...")
    listings = parse_listings(resp.text)
    print(f"Found {len(listings)} raw card(s)")

    listings = clean_listings(listings)
    print(f"After cleaning/deduplication: {len(listings)} listing(s)")

    df = to_dataframe(listings)
    if output:
        base = output.rsplit(".", 1)[0]
        csv_path = base + ".csv"
        json_path = base + ".json"
        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump([job.to_dict() for job in listings], fh, indent=2, ensure_ascii=False)
        print(f"Saved: {csv_path}, {json_path}")
    else:
        print("\nListings:")
        print(df.to_string(index=False))

    analysis = analyse_market(listings)
    print()
    print_analysis(analysis)

    return listings


def main() -> int:
    import os

    url = os.getenv("ELEVVO_JOBS_URL", DEFAULT_URL)
    try:
        run_scraper(url, output="job_listings")
        return 0
    except RobotsBlockedError as exc:
        print(f"[blocked] {exc}")
        return 3
    except ScraperError as exc:
        print(f"[error] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

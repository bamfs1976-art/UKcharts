"""
UK Official Charts Scraper — v2
Scrapes Top 100 Singles and Albums from officialcharts.com
Date range: 1 August 2025 to current date

Requirements:
    python -m pip install requests beautifulsoup4

Usage:
    python uk_charts_scraper.py

Output:
    uk_singles_2025_2026.csv
    uk_albums_2025_2026.csv
"""

import requests
import csv
import time
import logging
from datetime import date, timedelta
from bs4 import BeautifulSoup

# ── Configuration ────────────────────────────────────────────────────────────

START_DATE = date(2025, 8, 1)
END_DATE   = date.today()

CHARTS = {
    "singles": "https://www.officialcharts.com/charts/singles-chart/{date}/7501/",
    "albums":  "https://www.officialcharts.com/charts/albums-chart/{date}/7502/",
}

OUTPUT_FILES = {
    "singles": "uk_singles_2025_2026.csv",
    "albums":  "uk_albums_2025_2026.csv",
}

CSV_HEADERS = ["chart_date", "position", "title", "artist", "last_week", "peak_position", "weeks_on_chart"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

DELAY_BETWEEN_REQUESTS = 2
MAX_RETRIES = 3

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_fridays(start: date, end: date) -> list:
    """Return every Friday between start and end (inclusive)."""
    d = start
    while d.weekday() != 4:  # advance to first Friday
        d += timedelta(days=1)
    days = []
    while d <= end:
        days.append(d)
        d += timedelta(weeks=1)
    return days


def fetch_page(url: str):
    """Fetch a URL with retries. Returns BeautifulSoup or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            elif resp.status_code == 404:
                log.warning(f"404 — chart not found: {url}")
                return None
            else:
                log.warning(f"HTTP {resp.status_code} on attempt {attempt}: {url}")
        except requests.RequestException as e:
            log.warning(f"Request error on attempt {attempt}: {e}")
        time.sleep(DELAY_BETWEEN_REQUESTS * attempt)
    log.error(f"Failed after {MAX_RETRIES} attempts: {url}")
    return None


def parse_chart(soup: BeautifulSoup, chart_date: str) -> list:
    """
    Parse chart entries using selectors confirmed from live site inspection.

    Structure observed:
      div.chart-item
        div.chart-item-content
          div.position          -> chart position number
          div.description.block
            p
              a.chart-name      -> track/album title
              a.chart-artist    -> artist name
            div.stats.no-audio
              ol
                li.movement     -> last week position
                li.peak         -> peak position
                li.weeks        -> weeks on chart
    """
    entries = []

    items = soup.select("div.chart-item")
    if not items:
        log.warning("No div.chart-item elements found — page structure may have changed")
        return entries

    for item in items:
        try:
            position = _text(item, "div.position")
            # officialcharts.com now uses "Number1" instead of "1"
            if position.lower().startswith("number"):
                position = position[6:]
            title    = _text(item, "a.chart-name")
            artist   = _text(item, "a.chart-artist")

            if not title or not position:
                continue

            last_week = ""
            peak      = ""
            weeks     = ""

            stats_items = item.select("div.stats li")
            for li in stats_items:
                li_class = " ".join(li.get("class", []))
                bold = li.select_one("span.font-bold")
                value = bold.get_text(strip=True) if bold else ""

                if "movement" in li_class:
                    last_week = value
                elif "peak" in li_class:
                    peak = value
                elif "weeks" in li_class:
                    weeks = value

            entries.append({
                "chart_date":     chart_date,
                "position":       position.strip(),
                "title":          title.strip(),
                "artist":         artist.strip(),
                "last_week":      last_week.strip(),
                "peak_position":  peak.strip(),
                "weeks_on_chart": weeks.strip(),
            })

        except Exception as e:
            log.debug(f"Skipped an entry due to parse error: {e}")
            continue

    return entries


def _text(element, selector: str) -> str:
    """Safe CSS selector text extraction."""
    node = element.select_one(selector)
    return node.get_text(strip=True) if node else ""


def scrape_chart(chart_type: str, chart_dates: list) -> list:
    """Scrape all dates for a given chart type."""
    url_template = CHARTS[chart_type]
    all_entries = []
    total = len(chart_dates)

    for i, chart_date in enumerate(chart_dates, start=1):
        date_str = chart_date.strftime("%Y%m%d")
        url = url_template.format(date=date_str)
        log.info(f"[{chart_type}] {i}/{total}  {chart_date}")

        soup = fetch_page(url)
        if soup is None:
            log.warning(f"Skipping {chart_date} — no data retrieved")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue

        entries = parse_chart(soup, chart_date.strftime("%Y-%m-%d"))

        if not entries:
            log.warning(f"No entries parsed for {chart_date}")
        else:
            log.info(f"  -> {len(entries)} entries parsed")
            all_entries.extend(entries)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    return all_entries


def save_csv(entries: list, filepath: str) -> None:
    """Write entries to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(entries)
    log.info(f"Saved {len(entries)} rows -> {filepath}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    chart_dates = get_fridays(START_DATE, END_DATE)
    log.info(f"Date range: {START_DATE} to {END_DATE}")
    log.info(f"Chart dates to scrape: {len(chart_dates)}")
    log.info(f"Charts: singles + albums")
    log.info("-" * 60)

    for chart_type, output_file in OUTPUT_FILES.items():
        log.info(f"Starting {chart_type.upper()} chart scrape...")
        entries = scrape_chart(chart_type, chart_dates)

        if entries:
            save_csv(entries, output_file)
            log.info(f"Completed {chart_type}: {len(entries)} total rows -> {output_file}")
        else:
            log.error(f"No data collected for {chart_type} — check log above for errors")

        log.info("-" * 60)

    log.info("All done. Upload the CSV files to Claude when ready.")


if __name__ == "__main__":
    main()

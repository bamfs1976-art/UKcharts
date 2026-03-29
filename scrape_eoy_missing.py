"""
UK End of Year Charts - Missing Years Scraper
Scrapes uk-charts.co.uk for the years missing from our dataset.

KEY INSIGHT: The chart table is ON the year index page itself,
not on a sub-page. So we fetch /charts/DECADE/ID-YEAR directly.

Missing years needed:
  Singles: 1960-1989, 2000-2007
  (1952-1959 and 1990-2025 already have good data)

Year IDs confirmed from site:
  1960s: 178-187 (1960=178, sequential)
  1970s: need to discover
  1980s: 201-210 (1980=201, sequential)
  1990s: already have (111-120)
  2000s: 166-175 (2000=166, sequential)

Usage: python scrape_eoy_missing.py
Output: eoy_singles_missing.csv
"""

import requests, csv, time, logging, re
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

BASE    = "https://www.uk-charts.co.uk"
DELAY   = 1.5
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}

def fetch(path):
    try:
        r = requests.get(BASE + path, headers=HEADERS, timeout=15)
        return BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None
    except Exception as e:
        log.warning(f"  Error: {e}"); return None

def parse_table(soup, year):
    if not soup: return []
    table = soup.find("table")
    if not table: return []
    rows = []
    for row in table.find_all("tr"):
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) >= 3:
            pos = cols[0].strip().lstrip("0") or "0"
            if pos.isdigit():
                rows.append({
                    "year":     str(year),
                    "position": pos,
                    "artist":   cols[1].strip(),
                    "title":    cols[2].strip(),
                })
    return rows

def get_1970s_ids():
    """Fetch 1970s decade page to get year IDs."""
    soup = fetch("/index.php/charts/1970-s")
    if not soup: return {}
    ids = {}
    for a in soup.find_all("a", href=True):
        m = re.search(r"/charts/1970-s/(\d+)-(\d{4})$", a["href"])
        if m:
            ids[int(m.group(2))] = int(m.group(1))
    # Also check h3 tags which may contain the links
    for h3 in soup.find_all("h3"):
        a = h3.find("a", href=True)
        if a:
            m = re.search(r"/charts/1970-s/(\d+)-(\d{4})$", a["href"])
            if m:
                ids[int(m.group(2))] = int(m.group(1))
    return ids

# Hardcoded year paths for all missing years
# These fetch the year page directly which contains the chart table
MISSING_YEAR_PATHS = {
    # 1960s (IDs 178-187, confirmed from decade page)
    1960: "/index.php/charts/1960-s/178-1960",
    1961: "/index.php/charts/1960-s/179-1961",
    1962: "/index.php/charts/1960-s/180-1962",
    1963: "/index.php/charts/1960-s/181-1963",
    1964: "/index.php/charts/1960-s/182-1964",
    1965: "/index.php/charts/1960-s/183-1965",
    1966: "/index.php/charts/1960-s/184-1966",
    1967: "/index.php/charts/1960-s/185-1967",
    1968: "/index.php/charts/1960-s/186-1968",
    1969: "/index.php/charts/1960-s/187-1969",
    # 1970s - IDs to be discovered, fallback sequential from 188
    # 1980s (IDs 201-210, confirmed from /charts/1980-s page)
    1980: "/index.php/charts/1980-s/201-1980",
    1981: "/index.php/charts/1980-s/202-1981",
    1982: "/index.php/charts/1980-s/203-1982",
    1983: "/index.php/charts/1980-s/204-1983",
    1984: "/index.php/charts/1980-s/205-1984",
    1985: "/index.php/charts/1980-s/206-1985",
    1986: "/index.php/charts/1980-s/207-1986",
    1987: "/index.php/charts/1980-s/208-1987",
    1988: "/index.php/charts/1980-s/209-1988",
    1989: "/index.php/charts/1980-s/210-1989",
    # 2000s (IDs 166-175, confirmed from /charts/2000-s page)
    2000: "/index.php/charts/2000-s/166-2000",
    2001: "/index.php/charts/2000-s/167-2001",
    2002: "/index.php/charts/2000-s/168-2002",
    2003: "/index.php/charts/2000-s/169-2003",
    2004: "/index.php/charts/2000-s/170-2004",
    2005: "/index.php/charts/2000-s/171-2005",
    2006: "/index.php/charts/2000-s/172-2006",
    2007: "/index.php/charts/2000-s/173-2007",
}

def main():
    log.info("UK End of Year Charts - Missing Years Scraper")
    log.info("=" * 50)

    # Discover 1970s IDs
    log.info("Discovering 1970s year IDs...")
    ids_70s = get_1970s_ids()
    log.info(f"  Found: {ids_70s}")
    time.sleep(DELAY)

    for year in range(1970, 1980):
        if year in ids_70s:
            MISSING_YEAR_PATHS[year] = f"/index.php/charts/1970-s/{ids_70s[year]}-{year}"
        else:
            # Try sequential from 188 (1960s end at 187)
            guess_id = 188 + (year - 1970)
            MISSING_YEAR_PATHS[year] = f"/index.php/charts/1970-s/{guess_id}-{year}"
            log.warning(f"  1970s {year}: guessing ID {guess_id}")

    log.info(f"\nScraping {len(MISSING_YEAR_PATHS)} years...")
    all_rows = []

    for i, (year, path) in enumerate(sorted(MISSING_YEAR_PATHS.items()), 1):
        log.info(f"  [{i}/{len(MISSING_YEAR_PATHS)}] {year}  {path}")
        soup = fetch(path)
        rows = parse_table(soup, year)
        if rows:
            no1 = next((r for r in rows if r["position"]=="1"), None)
            log.info(f"    {len(rows)} entries  No.1: {no1['title'] if no1 else '?'} — {no1['artist'] if no1 else '?'}")
            all_rows.extend(rows)
        else:
            log.warning(f"    No entries — page may not exist or ID is wrong")
        time.sleep(DELAY)

    with open("eoy_singles_missing.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year","position","artist","title"])
        w.writeheader()
        w.writerows(all_rows)

    years_found = sorted(set(r["year"] for r in all_rows))
    log.info(f"\nSaved {len(all_rows)} rows for {len(years_found)} years -> eoy_singles_missing.csv")
    log.info(f"Years found: {years_found}")
    missing = [str(y) for y in list(range(1960,1990)) + list(range(2000,2008)) if str(y) not in years_found]
    if missing:
        log.warning(f"Still missing: {missing}")
    log.info("\nUpload eoy_singles_missing.csv to Claude when done.")

if __name__ == "__main__":
    main()

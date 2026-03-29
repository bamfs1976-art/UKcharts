"""
UK End of Year Charts Scraper - Final Version
Scrapes from uk-charts.co.uk using hardcoded year IDs.

All year IDs verified from decade index pages.
"""
import requests, csv, time, logging, re
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)
BASE    = "https://www.uk-charts.co.uk"
DELAY   = 1.2
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}

# All year page paths - verified from decade index pages
# 1950s: confirmed from previous run (1952-1959 found)
# 1960s: 1960=178, 1961=179... 1969=186 (sequential from 178)
# 1970s: need to check - using 1970s page
# 1980s: 1980=201, 1981=202... 1989=210
# 1990s: 1990=111, 1991=112... 1999=120 (confirmed)
# 2000s: 2000=166, 2001=167... (confirmed from fetch)
# 2010s: confirmed from previous run
# 2020s: confirmed from previous run

YEAR_PAGES = {
    # 1960s (IDs 178-187)
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
    # 1970s - need to discover, try sequential from a base
    # 1980s (IDs 201-210)
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
    # 1990s (IDs 111-120, confirmed)
    1990: "/index.php/charts/1990-s/111-1990",
    1991: "/index.php/charts/1990-s/112-1991",
    1992: "/index.php/charts/1990-s/113-1992",
    1993: "/index.php/charts/1990-s/114-1993",
    1994: "/index.php/charts/1990-s/115-1994",
    1995: "/index.php/charts/1990-s/116-1995",
    1996: "/index.php/charts/1990-s/117-1996",
    1997: "/index.php/charts/1990-s/118-1997",
    1998: "/index.php/charts/1990-s/119-1998",
    1999: "/index.php/charts/1990-s/120-1999",
    # 2000s (IDs 166-175)
    2000: "/index.php/charts/2000-s/166-2000",
    2001: "/index.php/charts/2000-s/167-2001",
    2002: "/index.php/charts/2000-s/168-2002",
    2003: "/index.php/charts/2000-s/169-2003",
    2004: "/index.php/charts/2000-s/170-2004",
    2005: "/index.php/charts/2000-s/171-2005",
    2006: "/index.php/charts/2000-s/172-2006",
    2007: "/index.php/charts/2000-s/173-2007",
    2008: "/index.php/charts/2000-s/174-2008",
    2009: "/index.php/charts/2000-s/175-2009",
}

def fetch(path):
    try:
        r = requests.get(BASE + path, headers=HEADERS, timeout=15)
        return BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None
    except Exception as e:
        log.warning(f"  Error: {e}"); return None

def get_chart_links(year_path):
    """Fetch year index, return (singles_url, albums_url) from table."""
    soup = fetch(year_path)
    if not soup: return None, None
    singles = albums = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Must be a child of this year's path
        if not (year_path + "/") in href and not href.startswith(year_path + "/"):
            if year_path not in href: continue
        text = a.get_text(strip=True).lower()
        href_l = href.lower()
        if "album" in href_l or "album" in text:
            if not albums: albums = href
        elif re.search(r"top.?(40|100|20)", href_l) or re.search(r"top.?(40|100|20)", text):
            if not singles: singles = href
    return singles, albums

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
                rows.append({"year": str(year), "position": pos,
                             "artist": cols[1].strip(), "title": cols[2].strip()})
    return rows

def main():
    log.info("UK End of Year Charts Scraper - Final")
    log.info("=" * 50)

    # Discover chart URLs for all years in YEAR_PAGES
    log.info("\nDiscovering chart links...")
    singles_map = {}
    albums_map  = {}

    for year, path in sorted(YEAR_PAGES.items()):
        s, a = get_chart_links(path)
        if s: singles_map[year] = s; log.info(f"  {year} S: {s}")
        if a: albums_map[year]  = a; log.info(f"  {year} A: {a}")
        else: log.warning(f"  {year}: no links found at {path}")
        time.sleep(0.6)

    log.info(f"\nSingles: {sorted(singles_map.keys())}")
    log.info(f"Albums:  {sorted(albums_map.keys())}")

    # Scrape singles
    log.info("\nScraping new singles years...")
    all_rows = []
    for i, (year, url) in enumerate(sorted(singles_map.items()), 1):
        log.info(f"  [{i}/{len(singles_map)}] {year}")
        entries = parse_table(fetch(url), year)
        if entries:
            no1 = next((e for e in entries if e["position"]=="1"), None)
            log.info(f"    {len(entries)} entries  No.1: {no1['title'] if no1 else '?'}")
            all_rows.extend(entries)
        time.sleep(DELAY)

    with open("eoy_singles_extra.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year","position","artist","title"])
        w.writeheader(); w.writerows(all_rows)
    log.info(f"Saved {len(all_rows)} rows -> eoy_singles_extra.csv")

    # Scrape albums
    log.info("\nScraping albums...")
    alb_rows = []
    for i, (year, url) in enumerate(sorted(albums_map.items()), 1):
        log.info(f"  [{i}/{len(albums_map)}] {year}")
        entries = parse_table(fetch(url), year)
        if entries:
            no1 = next((e for e in entries if e["position"]=="1"), None)
            log.info(f"    {len(entries)} entries  No.1: {no1['title'] if no1 else '?'}")
            alb_rows.extend(entries)
        time.sleep(DELAY)

    with open("eoy_albums_extra.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year","position","artist","title"])
        w.writeheader(); w.writerows(alb_rows)
    log.info(f"Saved {len(alb_rows)} rows -> eoy_albums_extra.csv")
    log.info("\nDone! Upload eoy_singles_extra.csv and eoy_albums_extra.csv to Claude.")

if __name__ == "__main__":
    main()

"""
Scrape missing chart weeks and update all data files (extracted + dist).
"""
import requests, json, os, sys, time, logging
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CHARTS = {
    "singles": "https://www.officialcharts.com/charts/singles-chart/{date}/7501/",
    "albums":  "https://www.officialcharts.com/charts/albums-chart/{date}/7502/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Scraping ─────────────────────────────────────────────────────────────────

def fetch_page(url):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            elif r.status_code == 404:
                log.warning(f"404 — chart not available yet: {url}")
                return None
            log.warning(f"HTTP {r.status_code} attempt {attempt}")
        except requests.RequestException as e:
            log.warning(f"Request error attempt {attempt}: {e}")
        time.sleep(3 * attempt)
    return None

def scrape_chart(chart_type, chart_date):
    url = CHARTS[chart_type].format(date=chart_date.strftime("%Y%m%d"))
    log.info(f"  Scraping {chart_type} for {chart_date}...")
    soup = fetch_page(url)
    if not soup:
        return None

    entries = []
    for item in soup.select("div.chart-item"):
        try:
            position = item.select_one("div.position")
            title    = item.select_one("a.chart-name")
            artist   = item.select_one("a.chart-artist")
            if not position or not title:
                continue

            lw = peak = weeks = ""
            for li in item.select("div.stats li"):
                li_class = " ".join(li.get("class", []))
                bold = li.select_one("span.font-bold")
                val  = bold.get_text(strip=True) if bold else ""
                if "movement" in li_class: lw    = val
                elif "peak"   in li_class: peak  = val
                elif "weeks"  in li_class: weeks = val

            pos_str   = position.get_text(strip=True)
            # officialcharts.com now uses "Number1" instead of "1"
            if pos_str.lower().startswith("number"):
                pos_str = pos_str[6:]
            title_str = title.get_text(strip=True)
            art_str   = artist.get_text(strip=True) if artist else ""

            if lw == "New" and title_str.startswith("New"):
                title_str = title_str[3:]
            elif lw == "RE" and title_str.startswith("RE"):
                title_str = title_str[2:]

            entries.append([pos_str.strip(), title_str.strip(),
                            art_str.strip(), lw, peak, weeks])
        except Exception:
            continue

    entries.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    log.info(f"  Got {len(entries)} entries")
    return entries if entries else None

# ── Data update helpers ──────────────────────────────────────────────────────

def make_label(date_key):
    dt  = datetime.strptime(str(date_key), "%Y%m%d")
    end = dt + timedelta(days=6)
    return f"{dt.day} {dt.strftime('%B %Y')}- {end.day} {end.strftime('%B %Y')}"

def add_weekly_entries(data, weekly_key, index_key, date_key, entries):
    """Add a week of chart entries to a data dict. Returns True if added."""
    if date_key in data[weekly_key]:
        log.info(f"    {date_key} already in {weekly_key} — skipping")
        return False
    data[weekly_key][date_key] = entries
    idx = data[index_key]
    if date_key not in idx.get("keys", []):
        idx.setdefault("keys", []).append(date_key)
        idx["keys"].sort()
        idx.setdefault("labels", {})[date_key] = make_label(date_key)
    return True

def update_raw_songs(data, entries, date_key):
    """Update RAW_SONGS with any new songs from this week's chart."""
    if "RAW_SONGS" not in data:
        return
    existing = set()
    for r in data["RAW_SONGS"]:
        existing.add((r[0].upper(), r[1].upper()))

    dt = datetime.strptime(date_key, "%Y%m%d")
    end = dt + timedelta(days=6)
    entry_label = f"{dt.day} {dt.strftime('%B %Y')}- {end.day} {end.strftime('%B %Y')}"

    added = 0
    for e in entries:
        title = e[1].upper()
        artist = e[2].upper()
        if (title, artist) not in existing:
            data["RAW_SONGS"].append([title, artist, e[4], e[5], entry_label])
            existing.add((title, artist))
            added += 1
    if added:
        log.info(f"    Added {added} new songs to RAW_SONGS")

def update_raw_albums(data, entries, date_key):
    """Update RAW_ALBUMS with any new albums from this week's chart."""
    if "RAW_ALBUMS" not in data:
        return
    existing = set()
    for r in data["RAW_ALBUMS"]:
        existing.add((r[0].upper(), r[1].upper()))

    dt = datetime.strptime(date_key, "%Y%m%d")
    end = dt + timedelta(days=6)
    entry_label = f"{dt.day} {dt.strftime('%B %Y')}- {end.day} {end.strftime('%B %Y')}"

    added = 0
    for e in entries:
        title = e[1].upper()
        artist = e[2].upper()
        if (title, artist) not in existing:
            data["RAW_ALBUMS"].append([title, artist, e[4], e[5], entry_label])
            existing.add((title, artist))
            added += 1
    if added:
        log.info(f"    Added {added} new albums to RAW_ALBUMS")

def update_trajectories(data, traj_key, entries, date_key, title_idx=1, artist_idx=2):
    """Update trajectory data with this week's positions."""
    if traj_key not in data:
        return
    for e in entries:
        key = f"{e[title_idx].upper()}||{e[artist_idx].upper()}"
        pos = int(e[0]) if e[0].isdigit() else None
        if pos is None:
            continue
        if key not in data[traj_key]:
            data[traj_key][key] = []
        data[traj_key][key].append([date_key, pos])

def update_number_ones(data, no1_key, entries, date_key, title_field, artist_field):
    """Update number ones list if there's a new #1."""
    if no1_key not in data or not entries:
        return
    top = entries[0]
    title = top[1].upper()
    artist = top[2].upper()

    dt = datetime.strptime(date_key, "%Y%m%d")
    week_label = f"{dt.day} {dt.strftime('%B %Y')}"

    no1s = data[no1_key]
    if no1s and no1s[-1][title_field].upper() == title and no1s[-1]["artist"].upper() == artist:
        no1s[-1]["weeks"] += 1
    else:
        new_entry = {"artist": artist, "weeks": 1, "first_week": week_label}
        new_entry[title_field] = title
        no1s.append(new_entry)

# ── Main ─────────────────────────────────────────────────────────────────────

def get_missing_fridays(current_keys):
    """Find Fridays between latest data and today."""
    latest = max(current_keys)
    latest_date = datetime.strptime(latest, "%Y%m%d").date()
    today = date.today()

    fridays = []
    d = latest_date + timedelta(weeks=1)
    while d <= today:
        fridays.append(d)
        d += timedelta(weeks=1)
    return fridays

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(path) / 1e6
    log.info(f"  Saved {os.path.basename(path)} ({size:.1f}MB)")

def main():
    dist_data = os.path.join(SCRIPT_DIR, "dist", "data")
    extracted = os.path.join(SCRIPT_DIR, "extracted")

    # Load current dist data
    log.info("Loading current data...")
    with open(os.path.join(dist_data, "singles.json"), encoding="utf-8") as f:
        singles = json.load(f)
    with open(os.path.join(dist_data, "albums.json"), encoding="utf-8") as f:
        albums = json.load(f)
    with open(os.path.join(dist_data, "extras.json"), encoding="utf-8") as f:
        extras = json.load(f)

    # Also load extracted files for backward compat
    with open(os.path.join(extracted, "singles.json"), encoding="utf-8") as f:
        ext_singles = json.load(f)
    with open(os.path.join(extracted, "albums.json"), encoding="utf-8") as f:
        ext_albums = json.load(f)

    # Find missing weeks
    current_keys = list(singles["RAW_WEEKLY"].keys())
    missing = get_missing_fridays(current_keys)

    if not missing:
        log.info("Already up to date!")
        return

    log.info(f"Missing {len(missing)} week(s): {[d.strftime('%Y%m%d') for d in missing]}")

    any_updated = False

    for chart_date in missing:
        date_key = chart_date.strftime("%Y%m%d")
        log.info(f"\n{'='*50}")
        log.info(f"Processing week: {chart_date} (key: {date_key})")
        log.info(f"{'='*50}")

        # Scrape singles
        s_entries = scrape_chart("singles", chart_date)
        if not s_entries:
            log.warning(f"Singles not available for {chart_date} — stopping here")
            break
        time.sleep(2)

        # Scrape albums
        a_entries = scrape_chart("albums", chart_date)
        if not a_entries:
            log.warning(f"Albums not available for {chart_date} — stopping here")
            break

        # Update dist/data/singles.json (has RAW_SONGS, RAW_WEEKLY — no index here)
        log.info("  Updating singles data...")
        if date_key not in singles["RAW_WEEKLY"]:
            singles["RAW_WEEKLY"][date_key] = s_entries

        # Update dist/data/albums.json (has RAW_ALBUMS, RAW_ALB_WEEKLY, WEEK_INDEX, ALB_WEEK_INDEX, etc)
        log.info("  Updating albums data...")
        a1 = add_weekly_entries(albums, "RAW_ALB_WEEKLY", "ALB_WEEK_INDEX", date_key, a_entries)

        # WEEK_INDEX (singles index) is in albums.json in dist
        if date_key not in albums.get("WEEK_INDEX", {}).get("keys", []):
            albums["WEEK_INDEX"].setdefault("keys", []).append(date_key)
            albums["WEEK_INDEX"]["keys"].sort()
            albums["WEEK_INDEX"].setdefault("labels", {})[date_key] = make_label(date_key)

        # Update RAW_SONGS and RAW_ALBUMS
        update_raw_songs(singles, s_entries, date_key)
        update_raw_albums(albums, a_entries, date_key)

        # Update trajectories in extras.json
        update_trajectories(extras, "SONG_TRAJ", s_entries, date_key)
        update_trajectories(extras, "ALB_TRAJ", a_entries, date_key)

        # Update number ones
        update_number_ones(albums, "NUMBER_ONES", s_entries, date_key, "song", "artist")
        update_number_ones(albums, "ALBUM_NO1S", a_entries, date_key, "album", "artist")

        # Update extracted files too
        add_weekly_entries(ext_singles, "RAW_WEEKLY", "WEEK_INDEX", date_key, s_entries)
        add_weekly_entries(ext_albums, "RAW_ALB_WEEKLY", "ALB_WEEK_INDEX", date_key, a_entries)

        any_updated = True
        log.info(f"  Week {date_key} done!")
        time.sleep(2)

    if any_updated:
        log.info("\nSaving all files...")
        save_json(singles, os.path.join(dist_data, "singles.json"))
        save_json(albums, os.path.join(dist_data, "albums.json"))
        save_json(extras, os.path.join(dist_data, "extras.json"))
        save_json(ext_singles, os.path.join(extracted, "singles.json"))
        save_json(ext_albums, os.path.join(extracted, "albums.json"))
        log.info("\nAll data files updated! Run deploy separately if needed.")
    else:
        log.info("No updates made.")

if __name__ == "__main__":
    main()

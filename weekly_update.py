"""
UK Charts Full Weekly Automation
Scrapes latest charts, updates JSON files, and deploys to Netlify.

Run manually once to set up, then Windows Task Scheduler handles it every Friday.

Usage:
    python weekly_update.py              # run update now
    python weekly_update.py --setup      # install Task Scheduler job
    python weekly_update.py --test       # test without scraping (dry run)

Requirements:
    python -m pip install requests beautifulsoup4
    npm install -g netlify-cli
    netlify login  (run once to authenticate)
"""

import requests, json, os, sys, time, logging, subprocess, shutil
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
EXTRACTED_DIR = os.path.join(SCRIPT_DIR, "extracted")
DIST_DATA_DIR = os.path.join(SCRIPT_DIR, "dist", "data")
LOG_FILE      = os.path.join(SCRIPT_DIR, "update_log.txt")

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

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

# ── Scraping ──────────────────────────────────────────────────────────────────

def get_latest_friday():
    today = date.today()
    days_since_friday = (today.weekday() - 4) % 7
    return today - timedelta(days=days_since_friday)

def fetch_page(url):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
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

# ── Data update ───────────────────────────────────────────────────────────────

def make_label(d):
    dt  = datetime.strptime(str(d), "%Y%m%d")
    end = dt + timedelta(days=6)
    return f"{dt.day} {dt.strftime('%B %Y')}- {end.day} {end.strftime('%B %Y')}"

def update_json(extracted_path, dist_path, data_key, index_key, entries, date_key):
    with open(extracted_path, encoding="utf-8") as f:
        data = json.load(f)

    if date_key in data[data_key]:
        log.info(f"  {date_key} already present — skipping")
        return False

    data[data_key][date_key] = entries

    # Update index
    idx = data[index_key]
    if date_key not in idx.get("keys", []):
        idx.setdefault("keys", []).append(date_key)
        idx.setdefault("labels", {})[date_key] = make_label(int(date_key))

    for path in [extracted_path, dist_path]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    size = os.path.getsize(dist_path) / 1e6
    log.info(f"  Saved {os.path.basename(dist_path)} ({size:.1f}MB)")
    return True

# ── Netlify deploy ────────────────────────────────────────────────────────────

def deploy_to_netlify():
    log.info("Deploying to Netlify...")
    dist_dir = os.path.join(SCRIPT_DIR, "dist")

    # Check netlify CLI is available
    netlify_cmd = shutil.which("netlify")
    if not netlify_cmd:
        log.error("  netlify CLI not found.")
        log.error("  Run:  npm install -g netlify-cli")
        log.error("  Then: netlify login")
        return False

    result = subprocess.run(
        ["netlify", "deploy", "--prod", "--dir", dist_dir],
        capture_output=True, text=True, cwd=SCRIPT_DIR
    )

    if result.returncode == 0:
        # Extract URL from output
        url_match = None
        for line in result.stdout.splitlines():
            if "netlify.app" in line or "Website URL" in line:
                url_match = line.strip()
        log.info(f"  Deploy successful!")
        if url_match:
            log.info(f"  {url_match}")
        return True
    else:
        log.error(f"  Deploy failed: {result.stderr[:500]}")
        return False

# ── Task Scheduler setup ──────────────────────────────────────────────────────

def setup_task_scheduler():
    """Register a Windows Task Scheduler job to run every Friday at 13:00."""
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    task_name   = "UKChartsWeeklyUpdate"

    # Build the schtasks command
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{python_path}" "{script_path}"',
        "/sc", "weekly",
        "/d",  "FRI",
        "/st", "13:00",
        "/f",   # force overwrite if exists
        "/rl", "HIGHEST",
    ]

    print(f"\nRegistering Windows Task Scheduler job: {task_name}")
    print(f"  Script:  {script_path}")
    print(f"  Python:  {python_path}")
    print(f"  Schedule: Every Friday at 13:00\n")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("Task registered successfully!")
        print(f"View it in Task Scheduler under: {task_name}")
        print("\nThe script will now run automatically every Friday at 13:00.")
        print("Make sure your PC is on and connected to the internet on Fridays.")
    else:
        print(f"Failed to register task: {result.stderr}")
        print("\nYou can register it manually in Task Scheduler:")
        print(f"  Program: {python_path}")
        print(f"  Arguments: {script_path}")
        print(f"  Trigger: Weekly, Friday, 13:00")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--test" in sys.argv
    setup   = "--setup" in sys.argv

    if setup:
        setup_task_scheduler()
        return

    log.info("=" * 50)
    log.info("UK Charts Weekly Update")
    log.info("=" * 50)

    if dry_run:
        log.info("DRY RUN — no scraping or saving")
        target = get_latest_friday()
        log.info(f"Would scrape: {target} (key: {target.strftime('%Y%m%d')})")
        return

    # Check required folders
    for path in [EXTRACTED_DIR, os.path.join(EXTRACTED_DIR, "singles.json"),
                 os.path.join(EXTRACTED_DIR, "albums.json")]:
        if not os.path.exists(path):
            log.error(f"Missing: {path} — run extract_data.py first")
            sys.exit(1)

    target      = get_latest_friday()
    date_key    = target.strftime("%Y%m%d")
    log.info(f"Target date: {target} (key: {date_key})")

    # Check if already up to date
    with open(os.path.join(EXTRACTED_DIR, "singles.json"), encoding="utf-8") as f:
        check = json.load(f)
    if date_key in check["RAW_WEEKLY"]:
        log.info("Already up to date — nothing to do.")
        return

    log.info("")

    # Scrape
    singles_entries = scrape_chart("singles", target)
    if not singles_entries:
        log.error("Singles scrape failed — aborting"); sys.exit(1)
    time.sleep(2)

    albums_entries = scrape_chart("albums", target)
    if not albums_entries:
        log.error("Albums scrape failed — aborting"); sys.exit(1)

    log.info("")

    # Update JSON files
    log.info("Updating data files...")
    s_updated = update_json(
        os.path.join(EXTRACTED_DIR, "singles.json"),
        os.path.join(DIST_DATA_DIR, "singles.json"),
        "RAW_WEEKLY", "WEEK_INDEX", singles_entries, date_key
    )
    a_updated = update_json(
        os.path.join(EXTRACTED_DIR, "albums.json"),
        os.path.join(DIST_DATA_DIR, "albums.json"),
        "RAW_ALB_WEEKLY", "ALB_WEEK_INDEX", albums_entries, date_key
    )

    log.info("")

    # Deploy
    if s_updated or a_updated:
        deployed = deploy_to_netlify()
        log.info("")
        log.info("=" * 50)
        log.info(f"Update complete for week {date_key}")
        log.info(f"  Singles: {'updated' if s_updated else 'skipped'}")
        log.info(f"  Albums:  {'updated' if a_updated else 'skipped'}")
        log.info(f"  Deployed: {'yes' if deployed else 'failed — upload manually'}")
    else:
        log.info("No changes — nothing deployed.")

    log.info("=" * 50)

if __name__ == "__main__":
    main()

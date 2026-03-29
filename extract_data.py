"""
UK Charts Data Extractor
Extracts all data constants from uk_charts_complete_updated.html
into separate JSON files for the new split architecture.

Usage:  python extract_data.py

Output files (all in same folder):
  extracted/singles.json    — RAW_WEEKLY + WEEK_INDEX
  extracted/albums.json     — RAW_ALB_WEEKLY + ALB_WEEK_INDEX
  extracted/stats.json      — SONG_TRAJ, ALB_TRAJ, YEAR_CTX, S, RAW_ALBUMS
  extracted/manifest.json   — counts and checksums for verification
"""

import re, os, sys, json
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")
OUT_DIR    = os.path.join(SCRIPT_DIR, "extracted")

def find_bounds(html, name):
    m = re.search(rf'const\s+{re.escape(name)}\s*=', html)
    if not m:
        raise ValueError(f"const {name} not found")
    depth, i, opened = 0, m.end(), False
    while i < len(html):
        c = html[i]
        if c == '{':
            depth += 1; opened = True
        elif c == '[' and not opened:
            # Handle array constants (not object)
            depth += 1; opened = True
        elif c in '{}[]':
            if c in '{[': depth += 1
            else:
                depth -= 1
                if opened and depth == 0:
                    end = i + 2 if i + 1 < len(html) and html[i+1] == ';' else i + 1
                    return m.start(), end
        i += 1
    raise ValueError(f"closing brace not found for {name}")

def extract_constant(html, name):
    """Extract a JS constant and return its raw value string."""
    s, e = find_bounds(html, name)
    block = html[s:e]
    eq = re.search(r'=\s*', block)
    value_str = block[eq.end():]
    if value_str.endswith(';'):
        value_str = value_str[:-1]
    return value_str.strip()

def parse_raw_weekly(value_str):
    """
    Parse RAW_WEEKLY / RAW_ALB_WEEKLY.
    Keys are quoted strings "YYYYMMDD", values are arrays of arrays.
    Returns a dict.
    """
    # Quote any unquoted integer keys just in case
    fixed = re.sub(r'(?<!["\d])(\d{8})(?=\s*:)', r'"\1"', value_str)
    return json.loads(fixed)

def parse_week_index(value_str):
    """Parse WEEK_INDEX / ALB_WEEK_INDEX — has keys array and labels object."""
    return json.loads(value_str)

def parse_generic(value_str):
    """Parse any other constant — try JSON directly."""
    try:
        return json.loads(value_str)
    except Exception:
        # Try fixing unquoted integer keys
        fixed = re.sub(r'(?<!["\d])(\d{8})(?=\s*:)', r'"\1"', value_str)
        return json.loads(fixed)

def main():
    print("UK Charts Data Extractor")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found."); sys.exit(1)

    Path(OUT_DIR).mkdir(exist_ok=True)

    print(f"Reading {os.path.basename(HTML_FILE)}...")
    html = open(HTML_FILE, encoding="utf-8").read()
    print(f"  {len(html):,} chars\n")

    manifest = {}
    errors = []

    # ── Singles data ──────────────────────────────────────────────────────
    print("Extracting singles data...")
    try:
        raw_weekly_str  = extract_constant(html, "RAW_WEEKLY")
        week_index_str  = extract_constant(html, "WEEK_INDEX")
        raw_weekly      = parse_raw_weekly(raw_weekly_str)
        week_index      = parse_week_index(week_index_str)

        singles = {
            "RAW_WEEKLY":  raw_weekly,
            "WEEK_INDEX":  week_index
        }
        path = os.path.join(OUT_DIR, "singles.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(singles, f, ensure_ascii=False, separators=(',', ':'))
        size = os.path.getsize(path) / 1e6
        weeks = len(raw_weekly)
        entries = sum(len(v) for v in raw_weekly.values())
        index_keys = len(week_index.get("keys", []))
        print(f"  singles.json: {size:.1f}MB")
        print(f"    RAW_WEEKLY:  {weeks} weeks, {entries:,} entries")
        print(f"    WEEK_INDEX:  {index_keys} keys")
        manifest["singles"] = {"weeks": weeks, "entries": entries, "index_keys": index_keys, "size_mb": round(size,1)}
    except Exception as ex:
        print(f"  ERROR: {ex}"); errors.append(f"singles: {ex}")

    print()

    # ── Albums data ───────────────────────────────────────────────────────
    print("Extracting albums data...")
    try:
        raw_alb_str     = extract_constant(html, "RAW_ALB_WEEKLY")
        alb_index_str   = extract_constant(html, "ALB_WEEK_INDEX")
        raw_alb         = parse_raw_weekly(raw_alb_str)
        alb_index       = parse_week_index(alb_index_str)

        albums = {
            "RAW_ALB_WEEKLY": raw_alb,
            "ALB_WEEK_INDEX": alb_index
        }
        path = os.path.join(OUT_DIR, "albums.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, separators=(',', ':'))
        size = os.path.getsize(path) / 1e6
        weeks = len(raw_alb)
        entries = sum(len(v) for v in raw_alb.values())
        index_keys = len(alb_index.get("keys", []))
        print(f"  albums.json: {size:.1f}MB")
        print(f"    RAW_ALB_WEEKLY: {weeks} weeks, {entries:,} entries")
        print(f"    ALB_WEEK_INDEX: {index_keys} keys")
        manifest["albums"] = {"weeks": weeks, "entries": entries, "index_keys": index_keys, "size_mb": round(size,1)}
    except Exception as ex:
        print(f"  ERROR: {ex}"); errors.append(f"albums: {ex}")

    print()

    # ── Stats / supporting data ───────────────────────────────────────────
    print("Extracting stats data...")
    stats = {}
    for const_name in ["SONG_TRAJ", "ALB_TRAJ", "YEAR_CTX", "RAW_ALBUMS"]:
        try:
            val_str = extract_constant(html, const_name)
            stats[const_name] = parse_generic(val_str)
            count = len(stats[const_name]) if isinstance(stats[const_name], (dict, list)) else 1
            print(f"  {const_name}: {count} entries")
        except Exception as ex:
            print(f"  {const_name}: skipped ({ex})")

    if stats:
        path = os.path.join(OUT_DIR, "stats.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, separators=(',', ':'))
        size = os.path.getsize(path) / 1e6
        print(f"  stats.json: {size:.1f}MB")
        manifest["stats"] = {"constants": list(stats.keys()), "size_mb": round(size,1)}

    print()

    # ── Manifest ──────────────────────────────────────────────────────────
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # ── Summary ───────────────────────────────────────────────────────────
    total_size = sum(
        os.path.getsize(os.path.join(OUT_DIR, f)) / 1e6
        for f in os.listdir(OUT_DIR)
        if f.endswith('.json')
    )

    print("=" * 50)
    if errors:
        print(f"Completed with {len(errors)} errors:")
        for e in errors: print(f"  {e}")
    else:
        print("All constants extracted successfully.")
    print(f"\nOutput folder: extracted/")
    print(f"Total JSON size: {total_size:.1f}MB")
    print(f"\nFiles created:")
    for f in sorted(os.listdir(OUT_DIR)):
        size = os.path.getsize(os.path.join(OUT_DIR, f)) / 1e6
        print(f"  {f}: {size:.1f}MB")

if __name__ == "__main__":
    main()

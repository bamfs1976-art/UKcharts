"""
UK Charts Index Rebuilder v4
Rebuilds WEEK_INDEX and ALB_WEEK_INDEX in the exact correct format:
  {
    "keys": ["19521114", "19521121", ...],
    "labels": {"19521114": "14 November 1952- 20 November 1952", ...}
  }

Usage:  python rebuild_indexes.py
Input/Output: uk_charts_complete_updated.html
"""

import re, os, sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

def find_bounds(html, name):
    m = re.search(rf'const\s+{re.escape(name)}\s*=', html)
    if not m:
        raise ValueError(f"const {name} not found")
    depth, i, opened = 0, m.end(), False
    while i < len(html):
        c = html[i]
        if c == '{':
            depth += 1
            opened = True
        elif c == '}':
            depth -= 1
            if opened and depth == 0:
                end = i + 2 if i + 1 < len(html) and html[i + 1] == ';' else i + 1
                return m.start(), end
        i += 1
    raise ValueError(f"closing brace not found for {name}")

def get_date_keys(html, name):
    """Extract all 8-digit date keys from a chart data constant."""
    s, e = find_bounds(html, name)
    block = html[s:e]
    quoted   = re.findall(r'"(\d{8})\s*"?\s*:', block)
    unquoted = re.findall(r'(?<!["\d])(\d{8})\s*:', block)
    all_keys = set(quoted) | set(unquoted)
    return sorted(int(k) for k in all_keys)

def make_label(date_int):
    dt  = datetime.strptime(str(date_int), "%Y%m%d")
    end = dt + timedelta(days=6)
    return f"{dt.day} {dt.strftime('%B %Y')}- {end.day} {end.strftime('%B %Y')}"

def build_index_js(date_ints):
    """
    Build the index in the exact format the site expects:
    {
      "keys":["19521114","19521121",...],
      "labels":{"19521114":"14 November 1952- 20 November 1952",...}
    }
    """
    # keys array
    keys_js = ",".join(f'"{d}"' for d in date_ints)

    # labels object
    label_entries = ",".join(
        f'"{d}":"{make_label(d)}"' for d in date_ints
    )

    return '{"keys":[' + keys_js + '],"labels":{' + label_entries + '}}'

def replace_constant(html, name, new_value_js):
    s, e     = find_bounds(html, name)
    eq_match = re.search(r'=\s*', html[s:e])
    eq_pos   = s + eq_match.end()
    suffix   = ";" if html[e - 1] == ";" else ""
    return html[:s] + html[s:eq_pos] + new_value_js + suffix + html[e:]

def main():
    print("UK Charts Index Rebuilder v4")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found."); sys.exit(1)

    print(f"Reading {os.path.basename(HTML_FILE)}...")
    html = open(HTML_FILE, encoding="utf-8").read()
    print(f"  {len(html):,} chars")

    print("\nReading date keys from RAW_WEEKLY...")
    singles_keys = get_date_keys(html, "RAW_WEEKLY")
    print(f"  Found {len(singles_keys)} weeks ({singles_keys[0]} to {singles_keys[-1]})")

    print("Reading date keys from RAW_ALB_WEEKLY...")
    albums_keys = get_date_keys(html, "RAW_ALB_WEEKLY")
    print(f"  Found {len(albums_keys)} weeks ({albums_keys[0]} to {albums_keys[-1]})")

    print("\nBuilding WEEK_INDEX...")
    singles_js = build_index_js(singles_keys)
    print(f"  {len(singles_keys)} keys, {len(singles_keys)} labels")

    print("Building ALB_WEEK_INDEX...")
    albums_js = build_index_js(albums_keys)
    print(f"  {len(albums_keys)} keys, {len(albums_keys)} labels")

    print("\nReplacing WEEK_INDEX...")
    html = replace_constant(html, "WEEK_INDEX", singles_js)

    print("Replacing ALB_WEEK_INDEX...")
    html = replace_constant(html, "ALB_WEEK_INDEX", albums_js)

    # Verify structure
    for name in ("WEEK_INDEX", "ALB_WEEK_INDEX"):
        s, e = find_bounds(html, name)
        block = html[s:e]
        has_keys   = '"keys":[' in block
        has_labels = '"labels":{' in block
        key_count  = len(re.findall(r'"(\d{8})"', block.split('"labels"')[0])) if '"labels"' in block else 0
        label_count = len(re.findall(r'"(\d{8})"', block.split('"labels"')[1])) if '"labels"' in block else 0
        status = f"keys:{has_keys} labels:{has_labels} — {key_count} keys, {label_count} labels"
        print(f"  {name}: {status}")

    print(f"\nSaving...")
    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"  Saved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")
    print("\nDone! Hard-refresh the browser to test.")

if __name__ == "__main__":
    main()

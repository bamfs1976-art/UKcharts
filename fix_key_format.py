"""
Fix Key Format
Converts bare integer keys (20250801:) injected by merge_chart_data.py
into quoted string keys ("20250801":) to match the original file format.

Run this ONCE on uk_charts_complete_updated.html, then run rebuild_indexes.py.

Usage:  python fix_key_format.py
"""

import re, os, sys

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

def fix_bare_integer_keys(html, const_name):
    """
    Within the named constant, convert bare integer keys:
        20250801:[...]
    to quoted string keys:
        "20250801":[...]
    Skips keys that are already quoted.
    """
    s, e = find_bounds(html, const_name)
    block = html[s:e]

    # Count bare keys before fixing
    bare_keys = re.findall(r'(?<!["\d])(\d{8})\s*:', block)
    count = len(bare_keys)

    # Quote any unquoted 8-digit key
    fixed = re.sub(r'(?<!["\d])(\d{8})(?=\s*:)', r'"\1"', block)

    print(f"  {const_name}: {count} bare keys converted to quoted strings")
    return html[:s] + fixed + html[e:]

def main():
    print("Fix Key Format")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found.")
        sys.exit(1)

    print(f"Reading {os.path.basename(HTML_FILE)}...")
    html = open(HTML_FILE, encoding="utf-8").read()
    print(f"  {len(html):,} chars")

    print("\nFixing RAW_WEEKLY...")
    html = fix_bare_integer_keys(html, "RAW_WEEKLY")

    print("Fixing RAW_ALB_WEEKLY...")
    html = fix_bare_integer_keys(html, "RAW_ALB_WEEKLY")

    print("\nSaving...")
    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"  Saved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")
    print("\nDone! Now run:  python rebuild_indexes.py")

if __name__ == "__main__":
    main()

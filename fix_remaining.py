"""
Fix remaining 2024 references and slider tick label.
Usage:  python fix_remaining.py
Input/Output: uk_charts_complete_updated.html
"""

import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

def main():
    print("Fix Remaining 2024 References")
    print("=" * 50)

    html = open(HTML_FILE, encoding="utf-8").read()
    changes = []

    # Fix every remaining 2024 occurrence, but ONLY in text/string contexts
    # Avoid touching data values like chart dates (19521114 etc)
    replacements = [
        # Birthday No.1 description text
        ('November 1952 to March 2024',  'November 1952 to March 2026'),
        ('November 1952 to 2024',        'November 1952 to 2026'),
        # Slider tick labels in HTML
        ('>2024<',                        '>2026<'),
        # Any remaining plain text references
        ('since 2024',   'since 2026'),
        ('until 2024',   'until 2026'),
        ('up to 2024',   'up to 2026'),
        ('to 2024.',     'to 2026.'),
        ('to 2024,',     'to 2026,'),
        # Year range strings
        ('2024"',  '2026"'),   # e.g. value="2024"  -- only at end of attr
    ]

    for old, new in replacements:
        count = html.count(old)
        if count:
            html = html.replace(old, new)
            changes.append(f"  '{old}' -> '{new}' ({count}x)")

    # Slider tick: look for the rightmost tick label which shows the end year
    # Pattern: <span ...>2024</span> or similar near "tick" class
    tick_pattern = r'(<(?:span|div)[^>]*tick[^>]*>)\s*2024\s*(</(?:span|div)>)'
    new_html, n = re.subn(tick_pattern, r'\g<1>2026\2', html)
    if n:
        html = new_html
        changes.append(f"  Slider tick label 2024 -> 2026 ({n}x)")

    print(f"Changes ({len(changes)}):")
    for c in changes:
        print(c)

    # Show any remaining 2024 in non-data contexts
    remaining = [(m.start(), html[max(0,m.start()-50):m.end()+50])
                 for m in re.finditer(r'(?<!\d)2024(?!\d)', html)
                 if not re.search(r'\d{8}', html[max(0,m.start()-8):m.end()+1])]
    if remaining:
        print(f"\nRemaining 2024 references ({len(remaining)}):")
        for pos, ctx in remaining[:15]:
            print(f"  char {pos}: {repr(ctx)}")

    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"\nSaved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")

if __name__ == "__main__":
    main()

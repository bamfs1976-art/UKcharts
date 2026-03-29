"""
Fix 2024 references and Era Time Machine year cap.

Usage:  python fix_2024_refs.py
Input/Output: uk_charts_complete_updated.html
"""

import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

def main():
    print("Fix 2024 References")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found."); sys.exit(1)

    html = open(HTML_FILE, encoding="utf-8").read()
    original_len = len(html)

    changes = []

    # 1. Header subtitle: 1952-2024 -> 1952-2026
    old = '<em>1952-2024</em>'
    new = '<em>1952-2026</em>'
    if old in html:
        html = html.replace(old, new)
        changes.append("Header subtitle: 1952-2024 -> 1952-2026")

    # 2. Any remaining 1952–2024 or 1952-2024 text (en-dash or hyphen variants)
    for variant in ['1952–2024', '1952-2024', '1952&#8211;2024']:
        count = html.count(variant)
        if count:
            html = html.replace(variant, variant.replace('2024', '2026'))
            changes.append(f"  '{variant}' replaced ({count} occurrences)")

    # 3. Era Time Machine slider: max year hardcoded as 2024
    # Typically appears as: max="2024" or max:2024 or maxYear=2024
    patterns = [
        (r'(max\s*=\s*["\'])2024(["\'])', r'\g<1>2026\2'),
        (r'(maxYear\s*[=:]\s*)2024\b', r'\g<1>2026'),
        (r'(max\s*:\s*)2024\b', r'\g<1>2026'),
        (r'between 1952 and 2024', 'between 1952 and 2026'),
        (r'1952 and 2024', '1952 and 2026'),
    ]
    for pattern, replacement in patterns:
        new_html, count = re.subn(pattern, replacement, html)
        if count:
            html = new_html
            changes.append(f"  Pattern '{pattern}' replaced ({count} occurrences)")

    # 4. Page title if it includes the year
    old = '<title>UK Charts 1952-2024</title>'
    new = '<title>UK Charts 1952-2026</title>'
    if old in html:
        html = html.replace(old, new)
        changes.append("Page title updated")

    # 5. Any stat text saying "up to 2024" or "through 2024"
    for phrase in ['up to 2024', 'through 2024', 'until 2024', 'to 2024']:
        if phrase in html:
            html = html.replace(phrase, phrase.replace('2024', '2026'))
            changes.append(f"  Phrase '{phrase}' updated")

    print(f"Changes made ({len(changes)}):")
    for c in changes:
        print(f"  {c}")

    if not changes:
        print("  No changes needed — checking what 2024 references remain...")
        matches = re.findall(r'.{40}2024.{40}', html)
        for m in matches[:10]:
            print(f"  {repr(m)}")

    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"\nSaved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")

if __name__ == "__main__":
    main()

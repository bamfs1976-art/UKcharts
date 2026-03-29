"""
Fix data corruption caused by fix_remaining.py.
Reverts date strings where the year was wrongly changed from 2024 to 2026
in chart entry date ranges like "9 February 2024- 15 February 2026"

Usage:  python fix_data_corruption.py
Input/Output: uk_charts_complete_updated.html
"""

import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

def main():
    print("Fix Data Corruption")
    print("=" * 50)

    html = open(HTML_FILE, encoding="utf-8").read()

    # The corruption pattern: a date range where the end year was wrongly
    # changed to 2026 but the actual chart week was in 2024.
    # Pattern: "DD Month 2024- DD Month 2026"  -> "DD Month 2024- DD Month 2024"
    # We only fix cases where a 2024 date range end was changed to 2026
    # These appear inside JSON strings as "e":"DD Month 2024- DD Month 2026"
    
    pattern = r'(\d{1,2} \w+ 2024- \d{1,2} \w+) 2026'
    
    def fix_match(m):
        return m.group(1) + ' 2024'
    
    new_html, count = re.subn(pattern, fix_match, html)
    print(f"  Reverted {count} corrupted date ranges (2026 -> 2024)")
    
    # Also fix the value="2026" that was correctly changed from the slider
    # but check we didn't accidentally revert that
    # The slider max should remain 2026 - check it's still there
    if 'max="2026"' in new_html:
        print("  Slider max=2026 preserved correctly")
    else:
        print("  WARNING: slider max may have been reverted - check manually")

    # Verify the birthday text fix is preserved
    if 'November 1952 to March 2026' in new_html:
        print("  Birthday text 'to March 2026' preserved correctly")

    open(HTML_FILE, "w", encoding="utf-8").write(new_html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"\nSaved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")
    print("Done.")

if __name__ == "__main__":
    main()

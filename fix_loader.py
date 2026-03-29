"""
Fix loader script - RAW_ALBUMS assignment issue.
Usage: python fix_loader.py
Input/Output: dist/index.html
"""
import os, re, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()

# Find and fix the loader script - ensure all globals assigned before buildIndexes
OLD = "showLoader('Building indexes…', 90);"
NEW = """showLoader('Building indexes…', 90);
        window.RAW_WEEKLY      = singles.RAW_WEEKLY      || {};
        window.WEEK_INDEX      = singles.WEEK_INDEX      || {};
        window.RAW_ALB_WEEKLY  = albums.RAW_ALB_WEEKLY   || {};
        window.ALB_WEEK_INDEX  = albums.ALB_WEEK_INDEX   || {};
        window.SONG_TRAJ       = stats.SONG_TRAJ         || {};
        window.ALB_TRAJ        = stats.ALB_TRAJ          || {};
        window.YEAR_CTX        = stats.YEAR_CTX          || {};
        window.RAW_ALBUMS      = stats.RAW_ALBUMS        || {};"""

# Also remove the duplicate assignment block that comes after
OLD2 = """        window.RAW_WEEKLY      = singles.RAW_WEEKLY;
        window.WEEK_INDEX      = singles.WEEK_INDEX;
        window.RAW_ALB_WEEKLY  = albums.RAW_ALB_WEEKLY;
        window.ALB_WEEK_INDEX  = albums.ALB_WEEK_INDEX;
        window.SONG_TRAJ       = stats.SONG_TRAJ  || {};
        window.ALB_TRAJ        = stats.ALB_TRAJ   || {};
        window.YEAR_CTX        = stats.YEAR_CTX   || {};
        window.RAW_ALBUMS      = stats.RAW_ALBUMS || {};"""

if OLD2 in html:
    html = html.replace(OLD2, "", 1)
    print("  Removed duplicate assignment block")

if OLD in html:
    html = html.replace(OLD, NEW, 1)
    print("  Fixed global assignments — all set before buildIndexes")
else:
    print("  WARNING: Could not find target string — checking loader structure...")
    # Find any loader script and show context
    m = re.search(r'buildIndexes\(\)', html)
    if m:
        print(f"  buildIndexes() found at char {m.start()}")
        print(repr(html[m.start()-400:m.start()+50]))

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: dist/index.html ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)")
print("Deploy with: netlify deploy --prod --dir=dist")

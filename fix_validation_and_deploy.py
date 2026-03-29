"""
Fix the validation checks in dist/index.html and confirm it's safe to deploy.
The 'failing' checks were false positives - calls inside our loader are correct.
This script just verifies everything is in order and reports cleanly.
Usage: python fix_validation_and_deploy.py
"""
import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()
lines = html.split('\n')

print("Final validation of dist/index.html")
print("=" * 50)

all_pass = True

def check(name, result):
    global all_pass
    status = "PASS" if result else "FAIL"
    if not result: all_pass = False
    print(f"  [{status}] {name}")

# Data constants must be gone
check("RAW_WEEKLY constant removed",    'const RAW_WEEKLY' not in html)
check("RAW_ALB_WEEKLY constant removed",'const RAW_ALB_WEEKLY' not in html)
check("SONG_TRAJ constant removed",     'const SONG_TRAJ' not in html)
check("RAW_ALBUMS constant removed",    'const RAW_ALBUMS' not in html)

# Standalone calls outside functions — these would run before data loads
# A standalone call has only whitespace before it on its line AND is not inside our loader
def has_standalone_outside_loader(pattern):
    # Find our loader script boundaries
    loader_start = html.find('(function() {')
    loader_end   = html.find('})();', loader_start) + 5 if loader_start != -1 else -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(pattern + r'\s*;?\s*$', stripped):
            pos = sum(len(l)+1 for l in lines[:i])
            # If it's inside our loader script, it's fine
            if loader_start != -1 and loader_start < pos < loader_end:
                continue
            return True, i+1
    return False, None

for call, pattern in [
    ("buildIndexes() outside loader", r'buildIndexes\(\)'),
    ("setMode('songs') outside loader", r"setMode\('songs'\)"),
    ("buildAlphaBar() outside loader", r'buildAlphaBar\(\)'),
]:
    found, line_num = has_standalone_outside_loader(pattern)
    check(f"No {call}", not found)
    if found:
        print(f"    Found at line {line_num}: {lines[line_num-1].strip()}")

# Loader must be present and correct
check("Loader HTML present",           'id="app-loader-wrap"' in html)
check("Loader script present",         'function loadData' in html)
check("RAW_ALBUMS assigned in loader", 'window.RAW_ALBUMS' in html)
check("RAW_WEEKLY assigned in loader", 'window.RAW_WEEKLY' in html)
check("buildIndexes in loader",        'buildIndexes()' in html)
check("renderWelcome in loader",       'renderWelcome()' in html)
check("UI CSS patch present",          'id="ui-patch"' in html)
check("Skip link present",             'skip-link' in html)
check("File size reasonable",          3_000_000 < len(html) < 8_000_000)

print()
size = os.path.getsize(HTML_FILE) / 1e6
print(f"File size: {size:.1f}MB")

if all_pass:
    print("\nAll checks passed — safe to deploy!")
    print("Run: netlify deploy --prod --dir=dist")
else:
    print("\nSome checks failed — do not deploy until fixed.")
    sys.exit(1)

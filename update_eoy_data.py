"""
Updates the EOY_SINGLES data in dist/index.html with the complete
72-year dataset (1954-2025, previously 34 years).

Replaces only the data — all functions and nav stay as-is.

Usage: python update_eoy_data.py
"""
import os, re, json, csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

# Build merged data
print("Building complete EOY dataset...")
all_rows = []
for fname in ["eoy_singles_1952_2025.csv", "eoy_singles_missing.csv"]:
    path = os.path.join(SCRIPT_DIR, fname)
    with open(path, encoding="utf-8") as f:
        all_rows.extend(csv.DictReader(f))

seen = set()
deduped = []
for r in all_rows:
    key = (r['year'], r['position'])
    if key not in seen:
        seen.add(key)
        deduped.append(r)

eoy = {}
for r in deduped:
    y = r['year']
    if y not in eoy: eoy[y] = []
    eoy[y].append([r['position'], r['title'], r['artist']])

eoy_sorted = {y: sorted(v, key=lambda x: int(x[0])) for y, v in sorted(eoy.items())}
years = sorted(eoy_sorted.keys())
EOY_JSON = json.dumps(eoy_sorted, separators=(',', ':'))
print(f"  {len(years)} years ({years[0]}–{years[-1]}), {len(EOY_JSON)//1024}KB")

# Read HTML
print("Reading dist/index.html...")
html = open(HTML_FILE, encoding="utf-8").read()
print(f"  {len(html):,} chars")

# Find and replace the EOY_SINGLES data
# The current block starts with: var EOY_SINGLES = {"1954":
old_pattern = re.compile(r'var EOY_SINGLES = \{"1\d\d\d":\[\[.*?\]\].*?\};', re.DOTALL)
m = old_pattern.search(html)
if m:
    old = m.group(0)
    print(f"  Found existing EOY_SINGLES ({len(old)//1024}KB)")
    html = html[:m.start()] + f'var EOY_SINGLES = {EOY_JSON};' + html[m.end():]
    print(f"  Replaced with {len(EOY_JSON)//1024}KB dataset")
else:
    print("  ERROR: Could not find existing EOY_SINGLES — is the EOY block present?")
    # Check if block exists at all
    if 'var EOY_SINGLES' in html:
        print("  'var EOY_SINGLES' exists but pattern didn't match")
    elif 'EOY_SINGLES' in html:
        print("  'EOY_SINGLES' exists in another form")
    else:
        print("  EOY_SINGLES not found at all — run fix_eoy_injection.py first")
    exit(1)

# Validate
checks = {
    "EOY_SINGLES present":   "var EOY_SINGLES = " in html,
    "Has 1960 data":         '"1960"' in html,
    "Has 1985 data":         '"1985"' in html,
    "Has 2003 data":         '"2003"' in html,
    "Has 2025 data":         '"2025"' in html,
    "renderEoySidebar":      "function renderEoySidebar" in html,
    "buildIndexes intact":   "function buildIndexes()" in html,
}
all_ok = True
for k, v in checks.items():
    print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if not v: all_ok = False

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: dist/index.html ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)")
if all_ok:
    print("All checks passed.\nDeploy:  netlify deploy --prod --dir=dist")
else:
    print("Some checks failed — review before deploying")

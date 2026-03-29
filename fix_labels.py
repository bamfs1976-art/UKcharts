"""Fix corrupted labels object and deploy EOY feature."""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()

# Fix the corrupted labels - replace the whole broken object with correct one
OLD_LABELS = "const labels = {songs:'Songs',artists:'Artists',weekly:'Weeks',no1:'Number Ones',xmas:'Christmas',ohw:'One-Hit Wonders',',welsh:'Welsh Artists','alb-songs':'Albums','alb-artists':'Album Artists','alb-weekly':'Album Weeks','alb-no1':'Album No.1s',stats:'Statistics'}"
NEW_LABELS = "const labels = {songs:'Songs',artists:'Artists',weekly:'Weeks',no1:'Number Ones',xmas:'Christmas',ohw:'One-Hit Wonders',welsh:'Welsh Artists','alb-songs':'Albums','alb-artists':'Album Artists','alb-weekly':'Album Weeks','alb-no1':'Album No.1s',stats:'Statistics'}"

if OLD_LABELS in html:
    html = html.replace(OLD_LABELS, NEW_LABELS, 1)
    print("Fixed labels object")
else:
    # Try regex fix of the specific corruption pattern
    html = re.sub(
        r"(ohw:'One-Hit Wonders'),',welsh:'Welsh Artists','",
        r"\1,welsh:'Welsh Artists',",
        html
    )
    print("Fixed labels via regex")

# Verify
m = re.search(r'const labels = \{[^}]+\}', html)
print(f"Labels now: {m.group(0) if m else 'NOT FOUND'}")

# Verify key checks
checks = {
    "stats:'Statistics'":  "stats:'Statistics'" in html,
    "welsh:'Welsh":        "welsh:'Welsh" in html,
    "no corrupt ',":       "Wonders','," not in html,
    "buildIndexes":        "function buildIndexes()" in html,
    "EOY_SINGLES":         "var EOY_SINGLES = " in html,
    "eoySetMode":          "window.eoySetMode" in html,
}
all_ok = True
for k, v in checks.items():
    print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if not v: all_ok = False

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: {os.path.getsize(HTML_FILE)/1e6:.1f}MB")
if all_ok:
    print("All OK — deploy with:  netlify deploy --prod --dir=dist")
else:
    print("Still issues — do not deploy")

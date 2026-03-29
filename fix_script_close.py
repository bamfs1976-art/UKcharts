"""Fix missing closing </script> tag before EOY block."""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()
lines = html.split('\n')

# Show context around the loader script end and EOY block start
print("Lines 2275-2292:")
for i in range(2274, min(2292, len(lines))):
    print(f"{i+1}: {lines[i][:120]}")

# The EOY block starts with <script> but the previous script block
# (the loader IIFE) is not closed. Find where the loader ends and fix it.
# The loader ends with: })(); followed by our <script> tag
# We need to insert </script> before our <script>

EOY_MARKER = '\n<script>\n/* UK Charts Year-End Singles Feature'
FIXED = '\n</script>\n<script>\n/* UK Charts Year-End Singles Feature'

if EOY_MARKER in html:
    html = html.replace(EOY_MARKER, FIXED, 1)
    print("\nInserted missing </script> before EOY block")
else:
    print("\nERROR: Could not find EOY marker")

# Verify
checks = {
    "EOY_SINGLES":        "var EOY_SINGLES = " in html,
    "eoySetMode":         "window.eoySetMode" in html,
    "buildIndexes":       "function buildIndexes()" in html,
    "script close before EOY": "</script>\n<script>\n/* UK Charts Year-End" in html,
}
all_ok = True
for k, v in checks.items():
    print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if not v: all_ok = False

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: {os.path.getsize(HTML_FILE)/1e6:.1f}MB")
if all_ok:
    print("Deploy:  netlify deploy --prod --dir=dist")
else:
    print("Still issues")

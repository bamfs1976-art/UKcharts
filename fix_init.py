"""
Fix init sequence - removes standalone boot calls that run before data loads.
Usage: python fix_init.py
Input/Output: dist/index.html
"""
import os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()
original = html

# Remove the standalone init block that runs before data is loaded
# These lines run immediately on parse, before our async loader finishes
INIT_BLOCK = """// ── INIT ──────────────────────────────────────────────────────
buildIndexes();
buildAlphaBar();
buildYearSelect();
buildAlbYearSelect();"""

if INIT_BLOCK in html:
    html = html.replace(INIT_BLOCK, "// Init moved to async loader")
    print("  Removed standalone init block (buildIndexes/buildAlphaBar/buildYearSelect)")
else:
    # Try removing individual lines
    for call in ['buildIndexes();', 'buildAlphaBar();', 'buildYearSelect();', 'buildAlbYearSelect();']:
        # Only remove standalone calls (not inside functions)
        pattern = rf'^({re.escape(call)})\s*$'
        new_html, n = re.subn(pattern, f'// {call} moved to loader', html, flags=re.MULTILINE)
        if n:
            html = new_html
            print(f"  Removed standalone: {call}")

# Now update our loader to call ALL the init functions
OLD_BOOT = """        buildIndexes();
        setMode('songs');
        renderWelcome();"""

NEW_BOOT = """        buildIndexes();
        buildAlphaBar();
        buildYearSelect();
        buildAlbYearSelect();
        setMode('songs');
        renderWelcome();"""

if OLD_BOOT in html:
    html = html.replace(OLD_BOOT, NEW_BOOT)
    print("  Updated loader to call full init sequence")
else:
    print("  WARNING: Could not find boot sequence in loader — searching...")
    m = re.search(r'buildIndexes\(\);\s*\n\s*setMode', html)
    if m:
        old = html[m.start():m.end()]
        new = old.replace('buildIndexes();', 
            'buildIndexes();\n        buildAlphaBar();\n        buildYearSelect();\n        buildAlbYearSelect();')
        html = html[:m.start()] + new + html[m.end():]
        print("  Updated loader via regex")

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: dist/index.html ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)")
print("Deploy with: netlify deploy --prod --dir=dist")

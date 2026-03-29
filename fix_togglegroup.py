"""
Fix toggleGroup function
Replaces the broken toggleGroup function with one that correctly
handles 'singles', 'albums', and 'explore' groups.

Usage:  python fix_togglegroup.py
Input/Output: uk_charts_complete_updated.html
"""

import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

OLD_FUNC = """function toggleGroup(g) {
  const other = g==='browse'?'explore':'browse';
  document.getElementById('grp-'+other+'-btn').classList.remove('open');
  document.getElementById('grp-'+other+'-drop').classList.remove('open');
  document.getElementById('grp-'+g+'-btn').classList.toggle('open');
  document.getElementById('grp-'+g+'-drop').classList.toggle('open');
}"""

NEW_FUNC = """function toggleGroup(g) {
  const all = ['singles','albums','explore'];
  all.forEach(name => {
    if (name !== g) {
      document.getElementById('grp-'+name+'-btn')?.classList.remove('open');
      document.getElementById('grp-'+name+'-drop')?.classList.remove('open');
    }
  });
  document.getElementById('grp-'+g+'-btn')?.classList.toggle('open');
  document.getElementById('grp-'+g+'-drop')?.classList.toggle('open');
}"""

def main():
    print("Fix toggleGroup")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found."); sys.exit(1)

    print(f"Reading {os.path.basename(HTML_FILE)}...")
    html = open(HTML_FILE, encoding="utf-8").read()

    if OLD_FUNC not in html:
        # Try to find it with flexible whitespace
        m = re.search(r'function toggleGroup\(g\)\s*\{[^}]+\}', html, re.DOTALL)
        if m:
            print(f"  Found toggleGroup at char {m.start()}")
            print(f"  Current function:\n{m.group(0)}")
            html = html[:m.start()] + NEW_FUNC + html[m.end():]
            print("  Replaced using regex match")
        else:
            print("  ERROR: Could not find toggleGroup function")
            sys.exit(1)
    else:
        html = html.replace(OLD_FUNC, NEW_FUNC)
        print("  Replaced using exact match")

    # Verify
    if NEW_FUNC in html:
        print("  Verified: new function is present")
    else:
        print("  WARNING: new function not found after replacement")

    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"\nSaved: {os.path.basename(HTML_FILE)} ({size:.1f} MB)")
    print("Done! Refresh the browser to test the dropdowns.")

if __name__ == "__main__":
    main()

"""
UK Charts Split Site Builder
Takes uk_charts_complete_updated.html and produces:
  - index.html        (UI only, loads data via fetch)
  - data/singles.json
  - data/albums.json
  - data/stats.json

Usage:  python build_split_site.py

All output goes into a  dist/  folder ready to upload to your web host.
"""

import re, os, sys, json, shutil
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")
EXTRACTED  = os.path.join(SCRIPT_DIR, "extracted")
DIST_DIR   = os.path.join(SCRIPT_DIR, "dist")
DATA_DIR   = os.path.join(DIST_DIR, "data")

# ── The fetch loader — replaces inline data constants ────────────────────────
# This script goes in place of all the const RAW_WEEKLY = {...}; blocks.
# It fetches the three JSON files, assigns the globals, then boots the app.

LOADER_SCRIPT = '''
  <script>
    // ── Data loader ──────────────────────────────────────────────────────
    // Fetches chart data from JSON files then boots the app.
    // Shows a loading screen while data is loading.

    function showLoader(msg) {
      const el = document.getElementById('app-loader');
      if (el) el.textContent = msg;
    }

    async function loadData() {
      const base = document.currentScript
        ? new URL('.', document.currentScript.src).href
        : './';

      try {
        showLoader('Loading singles data…');
        const [singlesRes, albumsRes, statsRes] = await Promise.all([
          fetch('data/singles.json'),
          fetch('data/albums.json'),
          fetch('data/stats.json'),
        ]);

        if (!singlesRes.ok) throw new Error('singles.json failed: ' + singlesRes.status);
        if (!albumsRes.ok)  throw new Error('albums.json failed: '  + albumsRes.status);
        if (!statsRes.ok)   throw new Error('stats.json failed: '   + statsRes.status);

        showLoader('Parsing data…');
        const [singles, albums, stats] = await Promise.all([
          singlesRes.json(),
          albumsRes.json(),
          statsRes.json(),
        ]);

        // Assign globals exactly as the original inline constants did
        window.RAW_WEEKLY      = singles.RAW_WEEKLY;
        window.WEEK_INDEX      = singles.WEEK_INDEX;
        window.RAW_ALB_WEEKLY  = albums.RAW_ALB_WEEKLY;
        window.ALB_WEEK_INDEX  = albums.ALB_WEEK_INDEX;
        window.SONG_TRAJ       = stats.SONG_TRAJ  || {};
        window.ALB_TRAJ        = stats.ALB_TRAJ   || {};
        window.YEAR_CTX        = stats.YEAR_CTX   || {};
        window.RAW_ALBUMS      = stats.RAW_ALBUMS || {};

        showLoader('');
        const loaderEl = document.getElementById('app-loader-wrap');
        if (loaderEl) loaderEl.style.display = 'none';

        // Boot the app — mirrors the original inline boot sequence
        buildIndexes();
        setMode('songs');
        renderWelcome();

      } catch(err) {
        showLoader('Error loading data: ' + err.message);
        console.error('Data load failed:', err);
      }
    }

    // Kick off loading once DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadData);
    } else {
      loadData();
    }
  </script>
'''

# ── Loading screen HTML — injected into <body> ────────────────────────────────
LOADER_HTML = '''
  <div id="app-loader-wrap" style="
    position:fixed;inset:0;
    background:#0a0a0a;
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    z-index:9999;font-family:sans-serif;color:#c9a84c;">
    <div style="font-size:2rem;font-weight:700;letter-spacing:.05em;margin-bottom:1rem">
      UK CHARTS
    </div>
    <div id="app-loader" style="font-size:.9rem;color:#888;letter-spacing:.1em">
      Loading…
    </div>
  </div>
'''

# ── Helpers ───────────────────────────────────────────────────────────────────

def find_bounds(html, name):
    m = re.search(rf'const\s+{re.escape(name)}\s*=', html)
    if not m:
        return None, None
    depth, i, opened = 0, m.end(), False
    while i < len(html):
        c = html[i]
        if c in '{[':
            depth += 1; opened = True
        elif c in '}]':
            depth -= 1
            if opened and depth == 0:
                end = i + 2 if i + 1 < len(html) and html[i+1] == ';' else i + 1
                return m.start(), end
        i += 1
    return None, None

def remove_constant(html, name):
    s, e = find_bounds(html, name)
    if s is None:
        print(f"  WARNING: {name} not found, skipping")
        return html, False
    # Also eat any leading whitespace/newline before the const
    while s > 0 and html[s-1] in ' \t':
        s -= 1
    # And the trailing newline
    if e < len(html) and html[e] == '\n':
        e += 1
    print(f"  Removed {name} ({(e-s)/1e6:.2f}MB)")
    return html[:s] + html[e:], True

def find_last_script_close(html):
    """Find the position just before the last </script> tag."""
    pos = html.rfind('</script>')
    return pos

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("UK Charts Split Site Builder")
    print("=" * 50)

    # Check inputs
    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found"); sys.exit(1)
    if not os.path.exists(EXTRACTED):
        print(f"ERROR: extracted/ folder not found — run extract_data.py first"); sys.exit(1)

    # Create dist structure
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    Path(DIST_DIR).mkdir()
    Path(DATA_DIR).mkdir()

    # Copy JSON data files
    print("Copying data files to dist/data/...")
    for fname in ["singles.json", "albums.json", "stats.json"]:
        src = os.path.join(EXTRACTED, fname)
        dst = os.path.join(DATA_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            size = os.path.getsize(dst) / 1e6
            print(f"  {fname}: {size:.1f}MB")
        else:
            print(f"  WARNING: {fname} not found in extracted/")

    # Read HTML
    print(f"\nReading HTML ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)...")
    html = open(HTML_FILE, encoding="utf-8").read()

    # Remove all data constants
    print("\nRemoving inline data constants...")
    for name in ["RAW_WEEKLY", "WEEK_INDEX", "RAW_ALB_WEEKLY", "ALB_WEEK_INDEX",
                 "SONG_TRAJ", "ALB_TRAJ", "YEAR_CTX", "RAW_ALBUMS"]:
        html, _ = remove_constant(html, name)

    # Remove the original boot calls that ran after the data
    # (setMode and renderWelcome at the bottom — we call them from the loader)
    boot_patterns = [
        r'\bsetMode\s*\(\s*[\'"]songs[\'"]\s*\)\s*;',
        r'\brenderWelcome\s*\(\s*\)\s*;(?!\s*\})',  # standalone call, not inside a function
    ]
    for pattern in boot_patterns:
        new_html, count = re.subn(pattern, '', html)
        if count:
            print(f"  Removed boot call matching {pattern[:40]}... ({count}x)")
            html = new_html

    # Inject loading screen at start of <body>
    html = html.replace('<body>', '<body>\n' + LOADER_HTML, 1)
    print("\nInjected loading screen")

    # Inject loader script just before </body>
    html = html.replace('</body>', LOADER_SCRIPT + '\n</body>', 1)
    print("Injected fetch loader script")

    # Write index.html
    out_path = os.path.join(DIST_DIR, "index.html")
    open(out_path, "w", encoding="utf-8").write(html)
    size = os.path.getsize(out_path) / 1e6
    print(f"\nWrote dist/index.html: {size:.1f}MB")

    # Summary
    print("\n" + "=" * 50)
    print("dist/ folder contents:")
    total = 0
    for root, dirs, files in os.walk(DIST_DIR):
        for f in sorted(files):
            path = os.path.join(root, f)
            rel  = os.path.relpath(path, DIST_DIR)
            size = os.path.getsize(path) / 1e6
            total += size
            print(f"  {rel}: {size:.1f}MB")
    print(f"\nTotal: {total:.1f}MB")
    print("\nDone! Upload the dist/ folder contents to your web host.")
    print("index.html must be in the root, data/ folder alongside it.")

if __name__ == "__main__":
    main()

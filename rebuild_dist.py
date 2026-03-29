"""
Complete rebuild of dist/index.html from the original working file.
Applies all changes in one clean pass:
  1. Strips all inline data constants
  2. Removes ALL standalone init calls (buildIndexes, buildAlphaBar, etc)
  3. Removes ALL previous loader scripts/HTML
  4. Injects ONE clean loader that: fetches data -> assigns globals -> runs init -> boots app
  5. Injects UI improvement CSS
  6. Injects loading screen HTML
  7. Validates the result before saving

Usage: python rebuild_dist.py
Input:  uk_charts_complete_updated.html  (original working file)
Output: dist/index.html
"""

import re, os, sys, json
from pathlib import Path

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SOURCE_HTML = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")
DIST_DIR    = os.path.join(SCRIPT_DIR, "dist")
OUTPUT_HTML = os.path.join(DIST_DIR, "index.html")

# ── Loading screen ────────────────────────────────────────────────────────────
LOADER_HTML = """<div id="app-loader-wrap" style="position:fixed;inset:0;background:#0a0a0a;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;z-index:9999;font-family:sans-serif;">
  <div style="font-size:2rem;font-weight:700;letter-spacing:.05em;color:#c9a84c;">UK CHARTS</div>
  <div style="width:32px;height:32px;border:2px solid #333;border-top-color:#c9a84c;border-radius:50%;animation:ldspin .8s linear infinite;"></div>
  <div style="width:240px;height:2px;background:#222;border-radius:2px;overflow:hidden;">
    <div id="loader-bar" style="height:100%;background:#c9a84c;border-radius:2px;transition:width .4s ease;width:0%;"></div>
  </div>
  <div id="app-loader" style="font-size:11px;color:#555;letter-spacing:.1em;text-transform:uppercase;">Loading…</div>
  <style>@keyframes ldspin{to{transform:rotate(360deg)}}</style>
</div>"""

# ── Data loader script — replaces ALL previous loader code ───────────────────
# This is the single source of truth for app initialisation.
LOADER_SCRIPT = """<script>
(function() {
  function progress(msg, pct) {
    var el = document.getElementById('app-loader');
    var bar = document.getElementById('loader-bar');
    if (el) el.textContent = msg;
    if (bar && pct !== undefined) bar.style.width = pct + '%';
  }

  function hideLoader() {
    var wrap = document.getElementById('app-loader-wrap');
    if (!wrap) return;
    wrap.style.opacity = '0';
    wrap.style.transition = 'opacity 0.3s ease';
    setTimeout(function() { wrap.style.display = 'none'; }, 320);
  }

  function loadData() {
    progress('Loading singles…', 5);

    var p1 = fetch('data/singles.json').then(function(r) {
      if (!r.ok) throw new Error('singles.json ' + r.status);
      progress('Parsing singles…', 25);
      return r.json();
    });

    var p2 = fetch('data/albums.json').then(function(r) {
      if (!r.ok) throw new Error('albums.json ' + r.status);
      progress('Loading albums…', 45);
      return r.json();
    });

    var p3 = fetch('data/stats.json').then(function(r) {
      if (!r.ok) throw new Error('stats.json ' + r.status);
      progress('Loading stats…', 65);
      return r.json();
    });

    Promise.all([p1, p2, p3]).then(function(results) {
      var singles = results[0];
      var albums  = results[1];
      var stats   = results[2];

      progress('Setting up data…', 80);

      // Assign all globals — must happen before any init function runs
      window.RAW_WEEKLY     = singles.RAW_WEEKLY     || {};
      window.WEEK_INDEX     = singles.WEEK_INDEX     || {};
      window.RAW_ALB_WEEKLY = albums.RAW_ALB_WEEKLY  || {};
      window.ALB_WEEK_INDEX = albums.ALB_WEEK_INDEX  || {};
      window.SONG_TRAJ      = stats.SONG_TRAJ        || {};
      window.ALB_TRAJ       = stats.ALB_TRAJ         || {};
      window.YEAR_CTX       = stats.YEAR_CTX         || {};
      window.RAW_ALBUMS     = stats.RAW_ALBUMS        || [];

      progress('Building indexes…', 90);

      // Run full init sequence in correct order
      buildIndexes();
      buildAlphaBar();
      buildYearSelect();
      buildAlbYearSelect();

      progress('Ready', 100);

      setTimeout(function() {
        hideLoader();
        setMode('songs');
        renderWelcome();
      }, 200);

    }).catch(function(err) {
      progress('Error: ' + err.message);
      var bar = document.getElementById('loader-bar');
      if (bar) bar.style.background = '#c0392b';
      console.error('Load failed:', err);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadData);
  } else {
    loadData();
  }
})();
</script>"""

# ── UI improvement CSS ────────────────────────────────────────────────────────
UI_CSS = """<style id="ui-patch">
/* Focus indicators — WCAG 2.4.7 */
:focus-visible {
  outline: 2px solid #c9a84c !important;
  outline-offset: 2px !important;
}
:focus:not(:focus-visible) { outline: none; }

/* Skip link — WCAG 2.4.1 */
.skip-link {
  position: absolute; top: -100px; left: 16px; z-index: 10000;
  background: #c9a84c; color: #1a0f08; padding: 8px 16px;
  font-weight: 700; font-size: 13px; border-radius: 0 0 4px 4px;
  text-decoration: none;
}
.skip-link:focus { top: 0 !important; outline: none !important; }

/* Contrast fixes — WCAG 1.4.3 */
.chart-artist, .col-artist, .alb-artist,
.entry-artist, .song-artist { color: #b8a898 !important; }

/* Touch targets — WCAG 2.5.8 */
.nav-drop-item, button.nav-drop-item,
.nav-dropdown-item { min-height: 44px !important; }

.week-item, .sidebar-week-item, .week-link {
  min-height: 36px !important;
  padding-top: 8px !important;
  padding-bottom: 8px !important;
}

/* Chart table headers — fix run-together text */
.chart-table th, table.chart th,
.alb-chart-table th, table.alb-chart th {
  padding: 10px 12px 8px !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  white-space: nowrap !important;
}

/* Album title truncation */
.alb-title, .col-title {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: 300px !important;
}

/* Reduced motion — WCAG 2.3.3 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def find_bounds(html, name):
    m = re.search(rf'const\s+{re.escape(name)}\s*=', html)
    if not m:
        return None, None
    depth, i, opened = 0, m.end(), False
    while i < len(html):
        c = html[i]
        if c in '{[': depth += 1; opened = True
        elif c in '}]':
            depth -= 1
            if opened and depth == 0:
                end = i+2 if i+1 < len(html) and html[i+1] == ';' else i+1
                return m.start(), end
        i += 1
    return None, None

def remove_constant(html, name):
    s, e = find_bounds(html, name)
    if s is None:
        return html, False
    # eat leading whitespace
    while s > 0 and html[s-1] in ' \t': s -= 1
    # eat trailing newline
    if e < len(html) and html[e] == '\n': e += 1
    return html[:s] + html[e:], True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("UK Charts — Complete dist rebuild")
    print("=" * 50)

    if not os.path.exists(SOURCE_HTML):
        print(f"ERROR: {SOURCE_HTML} not found")
        sys.exit(1)

    Path(DIST_DIR).mkdir(exist_ok=True)

    print(f"Reading source: {os.path.basename(SOURCE_HTML)} ({os.path.getsize(SOURCE_HTML)/1e6:.1f}MB)")
    html = open(SOURCE_HTML, encoding="utf-8").read()
    print(f"  {len(html):,} chars")

    # ── Step 1: Remove all data constants ────────────────────────────────────
    print("\nRemoving data constants...")
    for name in ["RAW_WEEKLY","WEEK_INDEX","RAW_ALB_WEEKLY","ALB_WEEK_INDEX",
                 "SONG_TRAJ","ALB_TRAJ","YEAR_CTX","RAW_ALBUMS"]:
        html, ok = remove_constant(html, name)
        status = f"removed ({(len(html)):,} chars remain)" if ok else "not found"
        print(f"  {name}: {status}")

    # ── Step 2: Remove ALL standalone init/boot calls ────────────────────────
    print("\nRemoving standalone init calls...")
    # These run on parse before data is ready — must all be removed
    init_calls = [
        r'buildIndexes\(\)\s*;',
        r'buildAlphaBar\(\)\s*;',
        r'buildYearSelect\(\)\s*;',
        r'buildAlbYearSelect\(\)\s*;',
        r'setMode\s*\(\s*[\'"]songs[\'"]\s*\)\s*;',
        r'renderWelcome\s*\(\s*\)\s*;(?!\s*\})',  # standalone only, not inside function body
    ]
    for pattern in init_calls:
        # Only remove lines that are standalone (not inside a function definition)
        # We match full lines that consist ONLY of the call
        full_line = rf'^\s*{pattern}\s*$'
        new_html, count = re.subn(full_line, '', html, flags=re.MULTILINE)
        if count:
            html = new_html
            print(f"  Removed {count}x: {pattern[:40]}")

    # Also remove the INIT comment block
    html = re.sub(r'//\s*[─\-]+\s*INIT\s*[─\-]+.*?\n', '', html)
    html = re.sub(r'//\s*Init moved to async loader\n', '', html)

    # ── Step 3: Remove any previous loader HTML/scripts ──────────────────────
    print("\nRemoving previous loader code...")

    # Remove old loader wrap div
    old_loader = re.search(r'<div id="app-loader-wrap".*?</div>\s*(?=\n|<)', html, re.DOTALL)
    if old_loader:
        html = html[:old_loader.start()] + html[old_loader.end():]
        print("  Removed old loader HTML")

    # Remove old loader scripts (any script containing loadData or showLoader)
    def remove_loader_scripts(h):
        result = h
        while True:
            m = re.search(r'<script[^>]*>\s*(?:function showLoader|async function loadData|\(function\s*\(\).*?loadData|\s*function progress)', result, re.DOTALL)
            if not m:
                break
            # Find the closing </script>
            end = result.find('</script>', m.start())
            if end == -1:
                break
            end += len('</script>')
            print(f"  Removed loader script ({(end-m.start())//1000}KB)")
            result = result[:m.start()] + result[end:]
        return result

    html = remove_loader_scripts(html)

    # Remove old skip links
    html = re.sub(r'<a[^>]*class="skip-link"[^>]*>.*?</a>\s*\n?', '', html, flags=re.DOTALL)

    # Remove old UI patch style blocks
    html = re.sub(r'<style id="ui-patch">.*?</style>\s*\n?', '', html, flags=re.DOTALL)
    html = re.sub(r'<style id="ui-improvements">.*?</style>\s*\n?', '', html, flags=re.DOTALL)

    # ── Step 4: Inject new loading screen after <body> ────────────────────────
    print("\nInjecting new loading screen...")
    html = html.replace('<body>', '<body>\n<a href="#main-content" class="skip-link">Skip to content</a>\n' + LOADER_HTML + '\n', 1)
    print("  Done")

    # ── Step 5: Inject UI CSS before </head> ─────────────────────────────────
    print("Injecting UI patch CSS...")
    html = html.replace('</head>', UI_CSS + '\n</head>', 1)
    print("  Done")

    # ── Step 6: Inject loader script before </body> ───────────────────────────
    print("Injecting loader script...")
    html = html.replace('</body>', LOADER_SCRIPT + '\n</body>', 1)
    print("  Done")

    # ── Step 7: Add id to main element for skip link ──────────────────────────
    if 'id="main-content"' not in html:
        html = re.sub(r'<main([^>]*)>', r'<main\1 id="main-content">', html, count=1)
        print("  Added id=main-content to <main>")

    # ── Step 8: Validate ──────────────────────────────────────────────────────
    print("\nValidating...")
    checks = {
        "Has loader HTML":      'id="app-loader-wrap"' in html,
        "Has loader script":    'function loadData' in html,
        "Has RAW_WEEKLY assign":'window.RAW_WEEKLY' in html,
        "Has RAW_ALBUMS assign":'window.RAW_ALBUMS' in html,
        "No standalone buildIndexes": not bool(re.search(r'^\s*buildIndexes\(\)\s*;', html, re.MULTILINE)),
        "No standalone setMode songs": not bool(re.search(r"^\s*setMode\('songs'\)\s*;", html, re.MULTILINE)),
        "Has UI CSS":           'id="ui-patch"' in html,
        "Has skip link":        'skip-link' in html,
        "Data constants removed": 'const RAW_WEEKLY' not in html,
    }

    all_pass = True
    for check, result in checks.items():
        status = "PASS" if result else "FAIL"
        if not result: all_pass = False
        print(f"  [{status}] {check}")

    if not all_pass:
        print("\nWARNING: Some checks failed. Review above before deploying.")
    else:
        print("\nAll checks passed!")

    # ── Step 9: Save ──────────────────────────────────────────────────────────
    open(OUTPUT_HTML, "w", encoding="utf-8").write(html)
    size = os.path.getsize(OUTPUT_HTML) / 1e6
    print(f"\nSaved: dist/index.html ({size:.1f}MB)")
    print("\nDeploy with:")
    print("  netlify deploy --prod --dir=dist")

if __name__ == "__main__":
    main()

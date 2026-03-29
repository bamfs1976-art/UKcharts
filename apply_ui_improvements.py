"""
Apply UI Improvements
Injects CSS patch and improved loading screen into dist/index.html.

Usage:  python apply_ui_improvements.py
Input/Output: dist/index.html
"""

import os, sys, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")
CSS_FILE   = os.path.join(SCRIPT_DIR, "ui_improvements.css")

# ── Improved loading screen with spinner + progress bar ──────────────────────
NEW_LOADER_HTML = '''  <div id="app-loader-wrap" style="position:fixed;inset:0;background:#0a0a0a;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;z-index:9999;font-family:sans-serif;">
    <div style="font-size:2rem;font-weight:700;letter-spacing:.05em;color:#F4AC45;">UK CHARTS</div>
    <div class="loader-spinner" style="width:32px;height:32px;border:2px solid #222;border-top-color:#F4AC45;border-radius:50%;animation:spin .8s linear infinite;"></div>
    <div class="loader-bar-track" style="width:240px;height:2px;background:#222;border-radius:2px;overflow:hidden;">
      <div class="loader-bar-fill" id="loader-bar" style="height:100%;background:#F4AC45;border-radius:2px;transition:width .4s ease;width:0%;"></div>
    </div>
    <div id="app-loader" style="font-size:11px;color:#6b5a4e;letter-spacing:.1em;text-transform:uppercase;">Loading…</div>
    <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
  </div>'''

# ── Skip to content link ──────────────────────────────────────────────────────
SKIP_LINK = '  <a href="#main-content" class="skip-link">Skip to content</a>\n'

# ── Updated loader script with progress bar support ──────────────────────────
NEW_LOADER_SCRIPT = '''  <script>
    function showLoader(msg, pct) {
      const el = document.getElementById('app-loader');
      const bar = document.getElementById('loader-bar');
      if (el) el.textContent = msg;
      if (bar && pct !== undefined) bar.style.width = pct + '%';
    }

    async function loadData() {
      try {
        showLoader('Loading singles data…', 10);
        const singlesRes = await fetch('data/singles.json');
        if (!singlesRes.ok) throw new Error('singles.json failed: ' + singlesRes.status);

        showLoader('Loading albums data…', 35);
        const albumsRes = await fetch('data/albums.json');
        if (!albumsRes.ok) throw new Error('albums.json failed: ' + albumsRes.status);

        showLoader('Loading chart stats…', 60);
        const statsRes = await fetch('data/stats.json');
        if (!statsRes.ok) throw new Error('stats.json failed: ' + statsRes.status);

        showLoader('Parsing data…', 75);
        const [singles, albums, stats] = await Promise.all([
          singlesRes.json(),
          albumsRes.json(),
          statsRes.json(),
        ]);

        showLoader('Building indexes…', 90);
        window.RAW_WEEKLY      = singles.RAW_WEEKLY;
        window.WEEK_INDEX      = singles.WEEK_INDEX;
        window.RAW_ALB_WEEKLY  = albums.RAW_ALB_WEEKLY;
        window.ALB_WEEK_INDEX  = albums.ALB_WEEK_INDEX;
        window.SONG_TRAJ       = stats.SONG_TRAJ  || {};
        window.ALB_TRAJ        = stats.ALB_TRAJ   || {};
        window.YEAR_CTX        = stats.YEAR_CTX   || {};
        window.RAW_ALBUMS      = stats.RAW_ALBUMS || {};

        showLoader('Ready!', 100);
        await new Promise(r => setTimeout(r, 300));

        const loaderEl = document.getElementById('app-loader-wrap');
        if (loaderEl) {
          loaderEl.style.opacity = '0';
          loaderEl.style.transition = 'opacity 0.3s ease';
          setTimeout(() => loaderEl.style.display = 'none', 300);
        }

        buildIndexes();
        setMode('songs');
        renderWelcome();

      } catch(err) {
        showLoader('Error: ' + err.message, 0);
        document.getElementById('loader-bar').style.background = '#E24B4A';
        console.error('Data load failed:', err);
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadData);
    } else {
      loadData();
    }
  </script>'''

def main():
    print("Apply UI Improvements")
    print("=" * 50)

    if not os.path.exists(HTML_FILE):
        print(f"ERROR: {HTML_FILE} not found"); sys.exit(1)
    if not os.path.exists(CSS_FILE):
        print(f"ERROR: {CSS_FILE} not found"); sys.exit(1)

    print(f"Reading {os.path.basename(HTML_FILE)} ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)...")
    html = open(HTML_FILE, encoding="utf-8").read()

    # 1. Read CSS patch
    css = open(CSS_FILE, encoding="utf-8").read()
    css_block = f'\n  <style id="ui-improvements">\n{css}\n  </style>\n'

    # 2. Inject CSS before </head>
    if '<style id="ui-improvements">' in html:
        # Replace existing patch
        html = re.sub(r'\n  <style id="ui-improvements">.*?</style>\n',
                      css_block, html, flags=re.DOTALL)
        print("  Updated existing CSS patch")
    else:
        html = html.replace('</head>', css_block + '</head>', 1)
        print("  Injected CSS patch before </head>")

    # 3. Replace loading screen HTML
    old_loader_pattern = r'<div id="app-loader-wrap".*?</div>\s*'
    if re.search(old_loader_pattern, html, re.DOTALL):
        html = re.sub(old_loader_pattern, NEW_LOADER_HTML + '\n  ', html, count=1, flags=re.DOTALL)
        print("  Replaced loading screen HTML")
    else:
        html = html.replace('<body>', '<body>\n' + NEW_LOADER_HTML, 1)
        print("  Injected loading screen HTML")

    # 4. Add skip link after <body>
    if 'class="skip-link"' not in html:
        html = html.replace('<body>\n' + NEW_LOADER_HTML, '<body>\n' + SKIP_LINK + NEW_LOADER_HTML, 1)
        print("  Added skip-to-content link")

    # 5. Replace loader script
    old_script_pattern = r'<script>\s*function showLoader.*?</script>'
    if re.search(old_script_pattern, html, re.DOTALL):
        html = re.sub(old_script_pattern, NEW_LOADER_SCRIPT.strip(), html, count=1, flags=re.DOTALL)
        print("  Replaced loader script with progress-bar version")
    else:
        html = html.replace('</body>', NEW_LOADER_SCRIPT + '\n</body>', 1)
        print("  Injected loader script")

    # 6. Add main-content ID to main element if missing (for skip link target)
    if 'id="main-content"' not in html:
        html = re.sub(r'<main([^>]*)>', r'<main\1 id="main-content">', html, count=1)
        print("  Added id='main-content' to <main> element")

    # Save
    open(HTML_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(HTML_FILE) / 1e6
    print(f"\nSaved: dist/index.html ({size:.1f}MB)")
    print("\nDone! Deploy dist/ to Netlify to see changes:")
    print("  netlify deploy --prod --dir=dist")

if __name__ == "__main__":
    main()

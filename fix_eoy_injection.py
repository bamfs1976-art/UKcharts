"""
EOY feature - minimal safe injection.
Only touches:
  1. Nav HTML (safe string replace)
  2. Appends a self-contained <script> block at end of file
  3. Nothing else in the existing JS is modified

The EOY script detects mode changes by monkey-patching setMode.
"""
import os, re, json, csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")
CSV_FILE   = os.path.join(SCRIPT_DIR, "eoy_singles_1952_2025.csv")

# ── Build data ────────────────────────────────────────────────────────────────
print("Building EOY data...")
with open(CSV_FILE, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

eoy = {}
for r in rows:
    y = r["year"]
    if y not in eoy: eoy[y] = []
    eoy[y].append([r["position"], r["title"], r["artist"]])

eoy_sorted = {y: sorted(v, key=lambda x: int(x[0])) for y, v in sorted(eoy.items())}
years = sorted(eoy_sorted.keys())
latest_year = years[-1]
EOY_JSON = json.dumps(eoy_sorted, separators=(",", ":"))
print(f"  {len(years)} years, {len(EOY_JSON)//1024}KB")

# ── Read file ─────────────────────────────────────────────────────────────────
print("Reading dist/index.html...")
html = open(HTML_FILE, encoding="utf-8").read()
print(f"  {len(html):,} chars")

# ── Strip ALL previous EOY attempts completely ────────────────────────────────
print("Stripping all previous EOY code...")

# Remove EOY script blocks (our injected blocks)
html = re.sub(r'<script>\s*const EOY_SINGLES=\{.*?</script>', '', html, flags=re.DOTALL)

# Remove eoyYear from S state if present
html = re.sub(r"\n\s*eoyYear:'[^']*',", '', html)

# Remove mi-eoy nav button line
html = re.sub(r'\s*<button[^>]*id="mi-eoy"[^>]*>.*?</button>\n?', '', html)

# Restore any labels corruption - check and fix line 836 area
# The labels line should end with stats:'Chart Statistics'};
# If we broke it, restore it
labels_pattern = re.search(r"const labels = \{[^}]+\}", html)
if labels_pattern:
    labels_text = labels_pattern.group(0)
    if 'eoy' in labels_text:
        fixed = re.sub(r",?eoy:'[^']*'", '', labels_text)
        html = html.replace(labels_text, fixed)
        print("  Removed eoy from labels")

# Remove eoy from exploreItems
html = html.replace(",'eoy'", "").replace("'eoy',", "")

# Remove eoy from mi- list
html = html.replace(",'mi-eoy'", "").replace("'mi-eoy',", "")

# Remove eoy from showSidebar
html = re.sub(r",\s*'eoy'", '', html)

# Remove eoy mode handler
html = re.sub(r"\s*else if\(mode===.eoy.\)[^\n]+\n", '\n', html)

print(f"  Stripped. Length: {len(html):,}")

# ── Verify existing code is intact ────────────────────────────────────────────
assert "function buildIndexes()" in html, "buildIndexes missing!"
assert html.count("const S = {") == 1, "S state duplicated!"
# Check labels not broken
m = re.search(r"const labels = \{[^}]+\}", html)
assert m, "labels object missing!"
print(f"  Labels OK: {m.group(0)[:80]}...")
print("  Core code intact")

# ── Now add ONLY the nav item and the EOY script block ────────────────────────

# 1. Add nav item (single safe replacement)
print("\n1. Adding nav item...")
STATS_BTN = '        <button class="nav-drop-item" id="mi-stats" onclick="setMode(\'stats\');closeGroups()">📊 Chart Statistics</button>'
EOY_BTN   = '        <button class="nav-drop-item" id="mi-eoy" onclick="eoySetMode();closeGroups()">🏆 Year-End Charts</button>'
if STATS_BTN in html:
    html = html.replace(STATS_BTN, EOY_BTN + '\n' + STATS_BTN, 1)
    print("   OK")
else:
    print("   WARNING: could not find stats button")

# 2. Append self-contained EOY script at end
# This script uses its own approach - overrides the app's setMode call
# so we don't need to touch setMode at all
print("2. Appending EOY script block...")

EOY_BLOCK = """
<script>
/* UK Charts Year-End Singles Feature
   Years available: """ + years[0] + """–""" + years[-1] + """ (""" + str(len(years)) + """ years)
*/
(function() {
  var EOY_SINGLES = """ + EOY_JSON + """;
  var _eoyYear = '""" + latest_year + """';

  // ── Sidebar renderer ──────────────────────────────────────
  function renderEoySidebar() {
    var yrs = Object.keys(EOY_SINGLES).sort().reverse();
    var html = yrs.map(function(y) {
      var no1 = EOY_SINGLES[y][0];
      return '<div class="s-item' + (_eoyYear===y?' active':'') + '" onclick="window._eoySelYear(\\'' + y + '\\')" role="button" tabindex="0">' +
        '<div class="s-item-title">' + y + '</div>' +
        '<div class="s-item-sub">' + esc(no1[1]) + ' &middot; ' + esc(no1[2]) + '</div>' +
        '</div>';
    }).join('');
    document.getElementById('sidebar-list').innerHTML = html || '<div class="empty-state">No data</div>';
  }

  // ── Year page renderer ────────────────────────────────────
  window._eoySelYear = function(year) {
    _eoyYear = year;
    // Update active in sidebar
    document.querySelectorAll('#sidebar-list .s-item').forEach(function(el) {
      el.classList.toggle('active', el.querySelector('.s-item-title') && el.querySelector('.s-item-title').textContent === year);
    });
    var entries = EOY_SINGLES[year] || [];
    if (!entries.length) { setContent('<div class="empty-state">No data for ' + year + '.</div>'); return; }
    var no1 = entries[0];
    var yrs = Object.keys(EOY_SINGLES).sort();
    var idx = yrs.indexOf(year);
    var prevY = idx > 0 ? yrs[idx-1] : null;
    var nextY = idx < yrs.length-1 ? yrs[idx+1] : null;

    var rows = entries.map(function(e) {
      var pos = e[0], title = e[1], artist = e[2];
      var pi = parseInt(pos);
      var pc = pi===1?'pos-1':pi===2?'pos-2':pi===3?'pos-3':'';
      var si = (typeof SONG_MAP !== 'undefined') ? (SONG_MAP[title+'||'+artist] != null ? SONG_MAP[title+'||'+artist] : -1) : -1;
      var ai = (typeof ARTIST_LIST !== 'undefined') ? ARTIST_LIST.indexOf(artist) : -1;
      return '<tr>' +
        '<td class="pos-cell ' + pc + '">' + pos + '</td>' +
        '<td><span class="song-link" onclick="if(' + si + '>=0)selSong(' + si + ')">' + esc(title) + '</span></td>' +
        '<td><span class="artist-link" onclick="if(' + ai + '>=0)selArtist(' + ai + ')">' + esc(artist) + '</span></td>' +
        '</tr>';
    }).join('');

    var prevBtn = '<button class="week-nav-btn"' + (!prevY?' disabled':'') + ' onclick="window._eoySelYear(\\'' + (prevY||'') + '\\')">&larr; ' + (prevY||'') + '</button>';
    var nextBtn = '<button class="week-nav-btn"' + (!nextY?' disabled':'') + ' onclick="window._eoySelYear(\\'' + (nextY||'') + '\\')">&rarr; ' + (nextY||'') + '</button>';

    var content = '<div class="page-fade">' +
      '<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:16px">' +
        '<div class="week-title-text">' + year + ' Year-End Singles Chart</div>' +
        '<div style="color:var(--faint);font-size:var(--text-xs);font-family:DM Mono,monospace">' + entries.length + ' entries</div>' +
      '</div>' +
      '<div class="week-nav">' + prevBtn + nextBtn + '</div>' +
      '<div class="no1-hero">' +
        '<div class="no1-crown">&#127942;</div>' +
        '<div>' +
          '<div class="no1-meta">Biggest Single of ' + year + '</div>' +
          '<div class="no1-song">' + esc(no1[1]) + '</div>' +
          '<div class="no1-artist">' + esc(no1[2]) + '</div>' +
        '</div>' +
      '</div>' +
      '<table class="chart-table">' +
        '<thead><tr><th style="width:40px">Pos</th><th>Song</th><th>Artist</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
      '</table>' +
    '</div>';
    setContent(content);
  };

  // ── Hook into nav button click ────────────────────────────
  // We intercept the eoySetMode call defined in the nav button
  window.eoySetMode = function() {
    // Use the app's setMode machinery for sidebar/nav state
    // but call our own sidebar and content renderers
    S.mode = 'eoy';
    // Clear active states on all nav items
    ['mi-songs','mi-artists','mi-weekly','mi-no1','mi-xmas',
     'mi-alb-songs','mi-alb-artists','mi-alb-weekly','mi-alb-no1',
     'mi-birthday','mi-date','mi-era','mi-welsh','mi-ohw','mi-stats','mi-eoy'
    ].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });
    var eoyEl = document.getElementById('mi-eoy');
    if (eoyEl) eoyEl.classList.add('active');
    // Show explore group as active
    var exploreBtn = document.getElementById('grp-explore-btn');
    if (exploreBtn) exploreBtn.classList.add('has-active');
    // Show sidebar
    var sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.style.display = '';
    // Hide controls not needed
    var alphaBar = document.getElementById('alpha-bar');
    if (alphaBar) alphaBar.style.display = 'none';
    var filterBar = document.getElementById('filter-bar');
    if (filterBar) filterBar.style.display = 'none';
    var sidebarYear = document.getElementById('sidebar-year');
    if (sidebarYear) sidebarYear.style.display = 'none';
    var sortBar = document.getElementById('sort-bar');
    if (sortBar) sortBar.style.display = 'none';
    // Labels
    var searchLabel = document.getElementById('search-label');
    if (searchLabel) searchLabel.textContent = 'Year-End';
    var searchInput = document.getElementById('search-input');
    if (searchInput) { searchInput.value = ''; searchInput.placeholder = 'Select a year…'; }
    // Render
    renderEoySidebar();
    window._eoySelYear(_eoyYear);
  };
})();
</script>"""

html = html + EOY_BLOCK

# ── Validate ──────────────────────────────────────────────────────────────────
print("\nValidating...")
checks = {
    "EOY_SINGLES data":    "var EOY_SINGLES = " in html,
    "renderEoySidebar":    "function renderEoySidebar" in html,
    "_eoySelYear":         "window._eoySelYear" in html,
    "eoySetMode":          "window.eoySetMode" in html,
    "mi-eoy nav":          'id="mi-eoy"' in html,
    "buildIndexes intact": "function buildIndexes()" in html,
    "labels not broken":   "stats:'Chart Statistics'" in html or "stats:\"Chart Statistics\"" in html,
    "single S = {":        html.count("const S = {") == 1,
    "no eoy in old JS":    ",'eoy'" not in html.split('<script>\n(function')[0],
}
all_ok = True
for k, v in checks.items():
    status = "PASS" if v else "FAIL"
    if not v: all_ok = False
    print(f"  [{status}] {k}")

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"\nSaved: {os.path.getsize(HTML_FILE)/1e6:.1f}MB")
if all_ok:
    print("All checks passed.\nDeploy:  netlify deploy --prod --dir=dist")
else:
    print("FAIL — do not deploy")

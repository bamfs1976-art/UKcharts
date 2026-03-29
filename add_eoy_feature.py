"""
Adds the Year-End Singles Chart feature to dist/index.html.

Changes:
  1. Injects EOY_SINGLES data constant
  2. Adds nav menu item (Explore dropdown)
  3. Updates setMode() to handle 'eoy' mode
  4. Adds renderEoySidebar() and renderEoyPage() functions
  5. Updates mode arrays (showSidebar, exploreItems, labels)

Usage: python add_eoy_feature.py
Input/Output: dist/index.html
"""
import os, re, json, csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")
CSV_FILE   = os.path.join(SCRIPT_DIR, "eoy_singles_1952_2025.csv")

# ── Build EOY data ────────────────────────────────────────────────────────────
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
print(f"  {len(years)} years: {years[0]}–{years[-1]}")

EOY_JSON = json.dumps(eoy_sorted, separators=(",", ":"))
EOY_CONST = f"const EOY_SINGLES = {EOY_JSON};"

# ── EOY render functions ──────────────────────────────────────────────────────
EOY_FUNCTIONS = r"""
// ── YEAR-END CHARTS ───────────────────────────────────────────
function renderEoySidebar() {
  const years = Object.keys(EOY_SINGLES).sort().reverse();
  document.getElementById('sidebar-list').innerHTML = years.map(y => `
    <div class="s-item${S.eoyYear===y?' active':''}" onclick="selEoyYear('${y}')" role="button" tabindex="0">
      <div class="s-item-title">${y}</div>
      <div class="s-item-sub">${esc(EOY_SINGLES[y][0][1])} · ${esc(EOY_SINGLES[y][0][2])}</div>
    </div>`).join('') || '<div class="empty-state">No data</div>';
}

function selEoyYear(year) {
  S.eoyYear = year;
  renderEoySidebar();
  const entries = EOY_SINGLES[year] || [];
  if (!entries.length) { setContent('<div class="empty-state">No data for this year.</div>'); return; }
  const no1 = entries[0];
  const years = Object.keys(EOY_SINGLES).sort();
  const idx = years.indexOf(year);
  const prevY = idx > 0 ? years[idx-1] : null;
  const nextY = idx < years.length-1 ? years[idx+1] : null;

  const rows = entries.map(e => {
    const [pos, title, artist] = e;
    const pi = parseInt(pos);
    const posClass = pi===1?'pos-1':pi===2?'pos-2':pi===3?'pos-3':'';
    return `<tr>
      <td class="pos-cell ${posClass}" aria-label="Position ${pos}">${pos}</td>
      <td><span class="song-link" onclick="selSong(${SONG_MAP[title+'||'+artist]??-1})">${esc(title)}</span></td>
      <td><span class="artist-link" onclick="selArtist(${ARTIST_LIST.indexOf(artist)})">${esc(artist)}</span></td>
    </tr>`;
  }).join('');

  setContent(`
    <div class="page-fade">
      <div style="display:flex;align-items:baseline;gap:var(--sp-4);margin-bottom:var(--sp-4)">
        <div class="week-title-text">${year} Year-End Singles Chart</div>
        <div style="color:var(--faint);font-size:var(--text-xs);font-family:'DM Mono',monospace">${entries.length} entries</div>
      </div>
      <div class="week-nav">
        <button class="week-nav-btn" ${!prevY?'disabled':''} onclick="selEoyYear('${prevY||''}')">← ${prevY||''}</button>
        <button class="week-nav-btn" ${!nextY?'disabled':''} onclick="selEoyYear('${nextY||''}')">→ ${nextY||''}</button>
      </div>
      <div class="no1-hero">
        <div class="no1-crown">🏆</div>
        <div>
          <div class="no1-meta">Biggest Single of ${year}</div>
          <div class="no1-song">${esc(no1[1])}</div>
          <div class="no1-artist">${esc(no1[2])}</div>
        </div>
      </div>
      <table class="chart-table">
        <thead><tr>
          <th style="width:36px">Pos</th>
          <th>Song</th>
          <th>Artist</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`);
}
"""

# ── Read HTML ─────────────────────────────────────────────────────────────────
print("Reading dist/index.html...")
html = open(HTML_FILE, encoding="utf-8").read()
original_len = len(html)

# ── 1. Inject EOY_SINGLES constant before </script> of the main script block ─
print("1. Injecting EOY_SINGLES constant...")
# Insert before buildIndexes function
if "EOY_SINGLES" in html:
    # Update existing
    html = re.sub(r'const EOY_SINGLES\s*=\s*\{.*?\};',
                  EOY_CONST, html, count=1, flags=re.DOTALL)
    print("   Updated existing EOY_SINGLES constant")
else:
    html = html.replace("function buildIndexes()",
                        EOY_CONST + "\n\nfunction buildIndexes()", 1)
    print("   Injected EOY_SINGLES constant")

# ── 2. Add eoyYear to state object ────────────────────────────────────────────
print("2. Adding eoyYear to state...")
latest_year = years[-1]
if "eoyYear" not in html:
    html = html.replace(
        "const S = {",
        f"const S = {{\n  eoyYear:'{latest_year}',"
    )
    print("   Added eoyYear to S")

# ── 3. Add nav menu item ──────────────────────────────────────────────────────
print("3. Adding nav menu item...")
OLD_STATS_ITEM = """        <button class="nav-drop-item" id="mi-stats" onclick="setMode('stats');closeGroups()">📊 Chart Statistics</button>"""
NEW_STATS_ITEM = """        <button class="nav-drop-item" id="mi-eoy" onclick="setMode('eoy');closeGroups()">🏆 Year-End Charts</button>
        <button class="nav-drop-item" id="mi-stats" onclick="setMode('stats');closeGroups()">📊 Chart Statistics</button>"""
if "mi-eoy" not in html:
    html = html.replace(OLD_STATS_ITEM, NEW_STATS_ITEM, 1)
    print("   Added Year-End Charts nav item")

# ── 4. Update setMode nav item list ──────────────────────────────────────────
print("4. Updating setMode nav arrays...")
html = html.replace(
    "'mi-birthday','mi-date','mi-era','mi-welsh','mi-ohw','mi-stats'",
    "'mi-birthday','mi-date','mi-era','mi-welsh','mi-ohw','mi-stats','mi-eoy'"
)

# Update exploreItems to include eoy
html = html.replace(
    "const exploreItems=['birthday','date','era','welsh','ohw','stats'];",
    "const exploreItems=['birthday','date','era','welsh','ohw','stats','eoy'];"
)

# Update showSidebar array to include eoy
html = re.sub(
    r"const showSidebar = \[([^\]]+)\]",
    lambda m: "const showSidebar = [" + m.group(1).rstrip() + ",'eoy']",
    html, count=1
)

# Update labels
html = html.replace(
    "const labels = {songs:'Songs',artists:'Artists',weekly:'Weeks',no1:'Number Ones',xmas:'Christmas',ohw:'One-Hit Wonders",
    "const labels = {songs:'Songs',artists:'Artists',weekly:'Weeks',no1:'Number Ones',xmas:'Christmas',ohw:'One-Hit Wonders',eoy:'Year-End"
)
# Close the labels properly - find and fix
html = re.sub(
    r"(eoy:'Year-End)([^}]*})",
    r"\1 Charts'\2",
    html, count=1
)

# ── 5. Add mode handler in setMode ────────────────────────────────────────────
print("5. Adding eoy mode handler...")
OLD_ELSE = "  else if(mode==='stats') { renderStatsPage(); }\n  else renderWelcome();"
NEW_ELSE = "  else if(mode==='stats') { renderStatsPage(); }\n  else if(mode==='eoy') { renderEoySidebar(); selEoyYear(S.eoyYear); }\n  else renderWelcome();"
html = html.replace(OLD_ELSE, NEW_ELSE, 1)
print("   Added eoy mode handler")

# ── 6. Add sidebar-year display for eoy mode ──────────────────────────────────
print("6. Updating sidebar year control...")
html = html.replace(
    "document.getElementById('sidebar-year').style.display = ['weekly','alb-weekly'].includes(mode)?'block':'none';",
    "document.getElementById('sidebar-year').style.display = ['weekly','alb-weekly'].includes(mode)?'block':'none';"
    # sidebar-year not needed for eoy - it uses its own sidebar list
)

# ── 7. Inject render functions ────────────────────────────────────────────────
print("7. Injecting EOY render functions...")
if "function renderEoySidebar" not in html:
    # Insert before the INIT comment or before </script>
    insert_before = "// ── INIT ──"
    if insert_before in html:
        html = html.replace(insert_before, EOY_FUNCTIONS + "\n" + insert_before, 1)
    else:
        # Fall back to inserting before closing script tag of main block
        html = html.replace("</script>\n</body>",
                            EOY_FUNCTIONS + "\n</script>\n</body>", 1)
    print("   Injected render functions")
else:
    # Update existing
    html = re.sub(r"// ── YEAR-END CHARTS ───.*?(?=// ──|\Z)",
                  EOY_FUNCTIONS + "\n", html, count=1, flags=re.DOTALL)
    print("   Updated existing render functions")

# ── Validate ──────────────────────────────────────────────────────────────────
print("\nValidating...")
checks = {
    "EOY_SINGLES constant":   "EOY_SINGLES" in html,
    "Nav menu item":          "mi-eoy" in html,
    "renderEoySidebar fn":    "function renderEoySidebar" in html,
    "selEoyYear fn":          "function selEoyYear" in html,
    "eoy in setMode":         "mode==='eoy'" in html,
    "eoy in exploreItems":    "'eoy'" in html,
}
all_ok = True
for k, v in checks.items():
    print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if not v: all_ok = False

# ── Save ──────────────────────────────────────────────────────────────────────
open(HTML_FILE, "w", encoding="utf-8").write(html)
size = os.path.getsize(HTML_FILE) / 1e6
print(f"\nSaved: dist/index.html ({size:.1f}MB)")
print(f"Size change: +{(len(html)-original_len)/1024:.0f}KB")
print("\nDeploy with:  netlify deploy --prod --dir=dist")

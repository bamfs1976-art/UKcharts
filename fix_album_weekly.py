"""
Fix album weekly view to match singles format exactly.
Replaces selAlbWeek() with a proper table layout matching selWeek().
Usage: python fix_album_weekly.py
Input: dist/index.html  (also updates in place)
"""
import os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()

# The old selAlbWeek function to replace
OLD = """function selAlbWeek(dk) {
  S.albWeekKey = dk;
  if(S.mode==='alb-weekly') {
    document.querySelectorAll('#sidebar-list .list-item').forEach(b=>{
      b.classList.toggle('active', b.onclick?.toString().includes(dk));
    });
  }
  const entries = RAW_ALB_WEEKLY[dk]||[];
  const label = ALB_WEEK_INDEX.labels[dk]||dk;
  setContent(`<div class="weekly-detail page-fade">
    <div class="song-detail-eyebrow">💿 Album Chart</div>
    <h2 class="weekly-title">${label}</h2>
    <div class="weekly-grid">
      <div class="wg-head"><span>Pos</span><span>Album</span><span>Artist</span><span>Move</span><span>Peak</span><span>Wks</span></div>
      ${entries.map(e=>`<div class="wg-row" onclick="selAlb(${ALB_MAP[e[1]+'||'+e[2]]??-1})">
        <span class="wg-pos ${e[0]==='1'?'pos-gold':''}">${e[0]}</span>
        <span class="wg-song">${e[1]}</span>
        <span class="wg-artist">${e[2]}</span>
        <span class="wg-move">${moveHtml(e[0],e[3])}</span>
        <span>${e[4]}</span>
        <span>${e[5]}</span>
      </div>`).join('')}
    </div>
  </div>`);
}"""

# New selAlbWeek — matches selWeek structure exactly
NEW = """function selAlbWeek(dk) {
  S.albWeekKey = dk;
  if(S.mode==='alb-weekly') {
    document.querySelectorAll('#sidebar-list .list-item').forEach(b=>{
      b.classList.toggle('active', b.onclick?.toString().includes(dk));
    });
  }
  const entries = RAW_ALB_WEEKLY[dk]||[];
  if(!entries.length){setContent('<div class="empty-state">No chart data for this week.</div>');return;}
  const label = ALB_WEEK_INDEX.labels[dk]||dk;
  const no1 = entries.find(e=>e[0]==='1')||entries[0];
  const keys = ALB_WEEK_INDEX.keys, idx = keys.indexOf(dk);
  const prevK = idx>0 ? keys[idx-1] : null;
  const nextK = idx<keys.length-1 ? keys[idx+1] : null;
  const rows = entries.map(e=>{
    const [pos,album,artist,lw,peak,weeks] = e;
    const pi = parseInt(pos);
    const posClass = pi===1?'pos-1':pi===2?'pos-2':pi===3?'pos-3':'';
    const pc = peakClass(peak);
    return `<tr>
      <td class="pos-cell ${posClass}" aria-label="Position ${pos}">${pos}</td>
      <td style="width:32px">${moveHtml(pos,lw)}</td>
      <td><span class="song-link" onclick="selAlb(${ALB_MAP[album+'||'+artist]??-1})">${esc(album)}</span></td>
      <td><span class="artist-link" onclick="selAlbArtist(${ALB_ARTIST_LIST.indexOf(artist)})">${esc(artist)}</span></td>
      <td style="text-align:center"><span class="peak-chip ${pc}" title="Peak position: ${peak}">${peak}</span></td>
      <td style="text-align:right;font-family:'DM Mono',monospace;font-size:var(--text-xs);color:var(--muted)">${weeks}</td>
    </tr>`;
  }).join('');
  setContent(`
    <div class="page-fade">
      <div style="display:flex;align-items:baseline;gap:var(--sp-4);margin-bottom:var(--sp-4)">
        <div class="week-title-text">${esc(label)}</div>
        <div style="color:var(--faint);font-size:var(--text-xs);font-family:'DM Mono',monospace">${entries.length} entries</div>
      </div>
      <div class="week-nav">
        <button class="week-nav-btn" ${!prevK?'disabled':''} onclick="selAlbWeek('${prevK||''}')">← Previous week</button>
        <button class="week-nav-btn" ${!nextK?'disabled':''} onclick="selAlbWeek('${nextK||''}')">Next week →</button>
      </div>
      <div class="no1-hero">
        <div class="no1-crown">💿</div>
        <div>
          <div class="no1-meta">Number One Album This Week</div>
          <div class="no1-song">${esc(no1[1])}</div>
          <div class="no1-artist">${esc(no1[2])}</div>
        </div>
      </div>
      <table class="chart-table">
        <thead><tr>
          <th style="width:36px">Pos</th><th style="width:32px"></th>
          <th>Album</th><th>Artist</th>
          <th style="text-align:center;width:40px" title="Peak position">Pk</th>
          <th style="text-align:right;width:40px">Wks</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`);
}"""

if OLD in html:
    html = html.replace(OLD, NEW)
    print("Replaced selAlbWeek function successfully")
else:
    print("ERROR: Could not find exact match for selAlbWeek — trying fuzzy match...")
    m = re.search(r'function selAlbWeek\(dk\)\s*\{', html)
    if m:
        # Find function end by brace counting
        start = m.start()
        depth, i, opened = 0, m.end(), False
        while i < len(html):
            c = html[i]
            if c == '{': depth += 1; opened = True
            elif c == '}':
                depth -= 1
                if opened and depth == 0:
                    end = i + 1
                    break
            i += 1
        old_func = html[start:end]
        html = html[:start] + NEW + html[end:]
        print(f"Replaced via fuzzy match ({len(old_func)} chars -> {len(NEW)} chars)")
    else:
        print("ERROR: selAlbWeek not found at all")
        exit(1)

open(HTML_FILE, "w", encoding="utf-8").write(html)
print(f"Saved: dist/index.html ({os.path.getsize(HTML_FILE)/1e6:.1f}MB)")
print("\nDeploy with:  netlify deploy --prod --dir=dist")

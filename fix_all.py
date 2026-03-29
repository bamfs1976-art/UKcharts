"""
Comprehensive fix for dist/index.html:
  1. Strip 'New' and 'RE' prefixes from RAW_SONGS entries
  2. Fix selAlbArtist to match selArtist card layout
  3. Fix sidebar date readability (s-item-title colour)
  4. Remove duplicate entries caused by New/RE prefix mismatch

Usage: python fix_all.py
Input/Output: dist/index.html
"""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

print("Reading dist/index.html...")
html = open(HTML_FILE, encoding="utf-8").read()
original_len = len(html)

# ── Fix 1: Strip New/RE prefixes from RAW_SONGS ──────────────────────────────
# RAW_SONGS entries look like: ["NewSONGTITLE","ARTIST",...]
# We need to strip the leading 'New' or 'RE' from the song title (index 0)
print("\n1. Fixing RAW_SONGS title prefixes...")

# Find RAW_SONGS constant boundaries
m_start = re.search(r'const RAW_SONGS\s*=\s*\[', html)
m_end_search = html.find('const WELSH_SONGS')
if m_start and m_end_search > 0:
    raw_songs_block = html[m_start.start():m_end_search]
    
    # Strip 'New' prefix from song titles: ["NewTITLE" -> ["TITLE"
    fixed_block = re.sub(r'\["New([A-Z])', r'["\1', raw_songs_block)
    # Strip 'RE' prefix from song titles: ["RETITLE" -> ["TITLE  
    fixed_block = re.sub(r'\["RE([A-Z])', r'["\1', fixed_block)
    
    # Count changes
    new_count = len(re.findall(r'\["New([A-Z])', raw_songs_block))
    re_count  = len(re.findall(r'\["RE([A-Z])', raw_songs_block))
    
    html = html[:m_start.start()] + fixed_block + html[m_end_search:]
    print(f"   Stripped 'New' from {new_count} titles")
    print(f"   Stripped 'RE' from {re_count} titles")
else:
    print("   WARNING: Could not find RAW_SONGS block")

# ── Fix 2: Fix selAlbArtist to match selArtist card layout ───────────────────
print("\n2. Fixing album artist page layout...")

OLD_ALB_ARTIST = """function selAlbArtist(idx) {
  const artist = ALB_ARTIST_LIST[idx];
  if(!artist) return;
  const albums = ALB_ARTIST_IDX[artist].sort((a,b)=>parseInt(a.peak)-parseInt(b.peak));
  setContent(`<div class="artist-detail page-fade">
    <div class="song-detail-eyebrow">🎤 Album Artist</div>
    <h2 class="song-detail-title">${artist}</h2>
    <div class="song-detail-stats">
      <span>${albums.length} charting album${albums.length!==1?'s':''}</span>
      <span>Best peak: #${albums[0].peak}</span>
    </div>
    <div class="song-detail-section">Discography</div>
    <div class="artist-albums-grid">
      ${albums.map(a=>`<div class="aa-row" onclick="selAlb(${ALB_MAP[a.album+'||'+a.artist]})">
        <span class="${peakClass(a.peak)} aa-peak">#${a.peak}</span>
        <div class="aa-info">
          <div class="aa-title">${a.album}</div>
          <div class="aa-meta">${a.weeks} weeks · First: ${a.entry}</div>
        </div>
      </div>`).join('')}
    </div>
  </div>`);
}"""

NEW_ALB_ARTIST = """function selAlbArtist(idx) {
  const artist = ALB_ARTIST_LIST[idx];
  if(!artist) return;
  const albums = ALB_ARTIST_IDX[artist].sort((a,b)=>(parseInt(a.peak)||999)-(parseInt(b.peak)||999));
  const best = Math.min(...albums.map(a=>parseInt(a.peak)||999));
  const no1s = albums.filter(a=>parseInt(a.peak)===1).length;
  const top10 = albums.filter(a=>parseInt(a.peak)<=10).length;
  const rows = albums.map(a=>{
    const p=parseInt(a.peak), pc=peakClass(p);
    return `<tr>
      <td><span class="song-link" onclick="selAlb(${ALB_MAP[a.album+'||'+a.artist]??-1})">${esc(a.album)}</span></td>
      <td style="text-align:center"><span class="peak-chip ${pc}">${a.peak}</span></td>
      <td class="mono-cell">${a.weeks}</td>
      <td class="mono-cell" style="font-size:var(--text-xs);color:var(--muted)">${esc(a.entry)}</td>
    </tr>`;
  }).join('');
  setContent(`
    <div class="card page-fade">
      <h1 style="font-family:'Playfair Display',serif;font-size:var(--text-3xl);font-weight:900;color:var(--cream);margin-bottom:var(--sp-2)">${esc(artist)}</h1>
      <p style="color:var(--muted);font-size:var(--text-sm);margin-bottom:var(--sp-5)">
        ${albums.length} charting album${albums.length!==1?'s':''}
        ${best<=1?' · <strong style=color:var(--gold)>UK Number One artist</strong>':' · Best peak: #'+best}
        ${no1s?' · '+no1s+' No.1 album'+(no1s>1?'s':''):''}
        ${top10?' · '+top10+' Top 10'+(top10>1?'s':''):''}
      </p>
      <div class="section-label">Discography</div>
      <table class="chart-table">
        <thead><tr><th>Album</th><th style="text-align:center">Peak</th><th>Weeks</th><th>Chart Entry</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`);
}"""

if OLD_ALB_ARTIST in html:
    html = html.replace(OLD_ALB_ARTIST, NEW_ALB_ARTIST)
    print("   Replaced selAlbArtist with card table layout")
else:
    print("   WARNING: Could not find exact selAlbArtist — trying fuzzy...")
    m = re.search(r'function selAlbArtist\(idx\)\s*\{', html)
    if m:
        start = m.start()
        depth, i, opened = 0, m.end(), False
        while i < len(html):
            c = html[i]
            if c == '{': depth+=1; opened=True
            elif c == '}':
                depth-=1
                if opened and depth==0:
                    html = html[:start] + NEW_ALB_ARTIST + html[i+1:]
                    print("   Replaced via fuzzy match")
                    break
            i+=1

# ── Fix 3: Improve sidebar date readability ───────────────────────────────────
print("\n3. Fixing sidebar date readability...")

# The s-item-title currently uses var(--cream) but the weekly render 
# overrides with font-size:var(--text-xs) making it tiny
# Fix: update the CSS class to be more readable
OLD_SITEM = """.s-item-title{font-size:var(--text-sm);font-weight:500;color:var(--cream);line-height:1.3}"""
NEW_SITEM = """.s-item-title{font-size:var(--text-sm);font-weight:500;color:var(--cream);line-height:1.3;opacity:0.9}"""

if OLD_SITEM in html:
    html = html.replace(OLD_SITEM, NEW_SITEM)

# The real fix: the renderWeeklySidebar uses inline font-size:var(--text-xs)
# which overrides the class. Fix the render function to not do that.
OLD_RENDER_SIDEBAR = """  document.getElementById('sidebar-list').innerHTML=list.map(k=>
    `<div class="s-item${S.weekKey===k?' active':''}" onclick="selWeek('${k}')" role="button" tabindex="0">
      <div class="s-item-title" style="font-size:var(--text-xs)">${esc(WEEK_INDEX.labels[k])}</div>
    </div>`).join('')||'<div class="empty-state">No weeks found</div>';"""

NEW_RENDER_SIDEBAR = """  document.getElementById('sidebar-list').innerHTML=list.map(k=>
    `<div class="s-item${S.weekKey===k?' active':''}" onclick="selWeek('${k}')" role="button" tabindex="0">
      <div class="s-item-title">${esc(WEEK_INDEX.labels[k])}</div>
    </div>`).join('')||'<div class="empty-state">No weeks found</div>';"""

if OLD_RENDER_SIDEBAR in html:
    html = html.replace(OLD_RENDER_SIDEBAR, NEW_RENDER_SIDEBAR)
    print("   Removed inline font-size override from sidebar items")
else:
    # Try to find and fix inline style override
    count = html.count('style="font-size:var(--text-xs)"')
    if count:
        # Only fix the one in sidebar items
        html = html.replace(
            '<div class="s-item-title" style="font-size:var(--text-xs)">',
            '<div class="s-item-title">'
        )
        print(f"   Removed inline font-size override ({count} instances)")

# Also fix album sidebar items if they have same issue
html = html.replace(
    '<div class="li-primary" style="font-size:var(--text-xs)">',
    '<div class="li-primary">'
)

# ── Fix 4: Update s-item CSS to be more readable ─────────────────────────────
print("\n4. Improving sidebar CSS readability...")

# Make sidebar items more readable - increase font size slightly
old_css = """.s-item{
  padding:var(--sp-2) var(--sp-4);
  border-left:3px solid transparent;
  cursor:pointer;transition:all var(--t-fast);
  min-height:44px;display:flex;flex-direction:column;justify-content:center;
}"""

new_css = """.s-item{
  padding:var(--sp-2) var(--sp-4);
  border-left:3px solid transparent;
  cursor:pointer;transition:all var(--t-fast);
  min-height:44px;display:flex;flex-direction:column;justify-content:center;
}"""

# The real readability fix is in s-item-title
old_title_css = """.s-item-title{font-size:var(--text-sm);font-weight:500;color:var(--cream);line-height:1.3}"""
new_title_css = """.s-item-title{font-size:0.8rem;font-weight:400;color:rgba(237,232,223,0.85);line-height:1.35}"""

if old_title_css in html:
    html = html.replace(old_title_css, new_title_css)
    print("   Updated s-item-title: brighter colour, better size")
elif '.s-item-title' in html:
    html = re.sub(
        r'\.s-item-title\{[^}]+\}',
        new_title_css,
        html
    )
    print("   Updated s-item-title via regex")

# ── Save ──────────────────────────────────────────────────────────────────────
open(HTML_FILE, "w", encoding="utf-8").write(html)
size = os.path.getsize(HTML_FILE) / 1e6
print(f"\nSaved: dist/index.html ({size:.1f}MB)")
print(f"Changed: {abs(len(html)-original_len):,} chars")
print("\nDeploy with:  netlify deploy --prod --dir=dist")

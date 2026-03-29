import json, os, shutil

BASE = r"C:\Users\abamf\Downloads\UK Charts"
DIST = os.path.join(BASE, "dist")

# Clean dist
if os.path.exists(DIST):
    shutil.rmtree(DIST)
os.makedirs(os.path.join(DIST, "data"), exist_ok=True)

# Load the big JSON
print("Loading uk_charts_data.json...")
with open(os.path.join(BASE, "uk_charts_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

# Define chunks
chunks = {
    "data/singles.json": ["RAW_SONGS", "RAW_WEEKLY"],
    "data/albums.json": ["RAW_ALBUMS", "RAW_ALB_WEEKLY", "WEEK_INDEX", "NUMBER_ONES", "ALB_WEEK_INDEX", "ALBUM_NO1S"],
    "data/extras.json": ["SONG_TRAJ", "ALB_TRAJ", "ONE_HIT_W", "WELSH_SONGS", "YEAR_CTX", "CHART_STATS", "XMAS_NO1S"],
}

for filename, keys in chunks.items():
    chunk = {k: data[k] for k in keys if k in data}
    path = os.path.join(DIST, filename)
    print(f"Writing {filename} ({len(chunk)} keys)...")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunk, f, separators=(",", ":"), ensure_ascii=False)
    size = os.path.getsize(path)
    print(f"  -> {size/1024/1024:.1f}MB")

# Now update the HTML to load 3 chunks instead of 1
print("Updating HTML...")
with open(os.path.join(BASE, "uk_charts_complete_updated.html"), "r", encoding="utf-8") as f:
    html = f.read()

# Find and replace the fetch/loader section
old_loader = """// ── LOAD DATA ──────────────────────────────────────────────────
(async function loadData() {
  const overlay = document.getElementById('loading-overlay');
  const msg = document.getElementById('loading-msg');
  const bar = document.getElementById('loading-bar');
  try {
    msg.textContent = 'Fetching chart data…';
    bar.style.width = '10%';
    const resp = await fetch('uk_charts_data.json');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    bar.style.width = '50%';
    msg.textContent = 'Parsing data…';
    const D = await resp.json();
    bar.style.width = '80%';
    msg.textContent = 'Initialising…';"""

new_loader = """// ── LOAD DATA ──────────────────────────────────────────────────
(async function loadData() {
  const overlay = document.getElementById('loading-overlay');
  const msg = document.getElementById('loading-msg');
  const bar = document.getElementById('loading-bar');
  try {
    msg.textContent = 'Loading singles data…';
    bar.style.width = '10%';
    const [r1, r2, r3] = await Promise.all([
      fetch('data/singles.json'),
      fetch('data/albums.json'),
      fetch('data/extras.json')
    ]);
    if (!r1.ok || !r2.ok || !r3.ok) throw new Error('Failed to load data files');
    bar.style.width = '40%';
    msg.textContent = 'Parsing singles…';
    const d1 = await r1.json();
    bar.style.width = '55%';
    msg.textContent = 'Parsing albums…';
    const d2 = await r2.json();
    bar.style.width = '70%';
    msg.textContent = 'Parsing extras…';
    const d3 = await d3.json();
    bar.style.width = '80%';
    msg.textContent = 'Initialising…';
    const D = Object.assign({}, d1, d2, d3);"""

# Hmm, let me just find the actual loader text in the file more carefully
# Let me search for the key parts
import re

# Find the loader function
match = re.search(r"// ── LOAD DATA.*?const D = .*?;", html, re.DOTALL)
if match:
    print(f"Found loader at position {match.start()}-{match.end()}")
    old_text = match.group(0)
    print(f"Old loader preview: {old_text[:200]}...")
else:
    print("Could not find loader pattern, searching alternatives...")
    # Try finding fetch('uk_charts_data.json')
    idx = html.find("uk_charts_data.json")
    if idx > 0:
        print(f"Found uk_charts_data.json reference at position {idx}")
        # Get surrounding context
        start = max(0, idx - 500)
        print(f"Context: ...{html[start:idx+200]}...")
    else:
        print("No reference to uk_charts_data.json found!")


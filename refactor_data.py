#!/usr/bin/env python3
"""
Extract inline JS data constants from uk_charts_complete_updated.html
into a separate JSON file, and modify the HTML to fetch that data.
"""

import json
import sys
import os

HTML_PATH = r'C:\Users\abamf\Downloads\UK Charts\uk_charts_complete_updated.html'
JSON_PATH = r'C:\Users\abamf\Downloads\UK Charts\uk_charts_data.json'
OUT_HTML  = r'C:\Users\abamf\Downloads\UK Charts\uk_charts_complete_updated.html'

CONST_NAMES = [
    'RAW_SONGS', 'RAW_WEEKLY', 'WEEK_INDEX', 'NUMBER_ONES',
    'RAW_ALBUMS', 'RAW_ALB_WEEKLY', 'ALB_WEEK_INDEX', 'ALBUM_NO1S',
    'SONG_TRAJ', 'ALB_TRAJ', 'CHART_STATS', 'XMAS_NO1S',
    'ONE_HIT_W', 'WELSH_SONGS', 'YEAR_CTX'
]

print("Reading HTML file...")
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Parse all data constants, handling multi-line ones
data = {}
lines_to_remove = set()  # 0-indexed line numbers to remove

i = 0
while i < len(lines):
    stripped = lines[i].strip()
    matched_name = None
    for name in CONST_NAMES:
        if name in data:
            continue
        prefix = f'const {name}'
        if stripped.startswith(prefix):
            matched_name = name
            break

    if matched_name:
        # Extract value - may span multiple lines
        first_line = lines[i]
        eq_idx = first_line.index('=', first_line.index(matched_name) + len(matched_name))
        value_start = first_line[eq_idx+1:]

        accumulated = value_start
        start_line = i
        lines_to_remove.add(i)

        # Check single-line case
        test = accumulated.strip()
        if test.endswith(';'):
            test = test[:-1].strip()

        try:
            parsed = json.loads(test)
            data[matched_name] = parsed
            print(f"  Line {i+1}: {matched_name} (single line, {len(test)} chars)")
            i += 1
            continue
        except json.JSONDecodeError:
            pass

        # Multi-line: keep accumulating
        j = i + 1
        while j < len(lines):
            lines_to_remove.add(j)
            accumulated += lines[j]
            test = accumulated.strip()
            if test.endswith(';'):
                test = test[:-1].strip()
            # Try to parse when we see a closing line
            if lines[j].strip() in ('};', '];'):
                try:
                    parsed = json.loads(test)
                    data[matched_name] = parsed
                    print(f"  Lines {start_line+1}-{j+1}: {matched_name} ({j - start_line + 1} lines, {len(test)} chars)")
                    break
                except json.JSONDecodeError:
                    pass
            j += 1

        if matched_name not in data:
            print(f"  ERROR: Could not parse {matched_name} starting at line {start_line+1}")
            sys.exit(1)

        i = j + 1
    else:
        i += 1

print(f"\nExtracted {len(data)} constants")
if len(data) != len(CONST_NAMES):
    missing = set(CONST_NAMES) - set(data.keys())
    print(f"WARNING: Missing constants: {missing}")

# Write JSON file
print(f"\nWriting JSON to {JSON_PATH}...")
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    f.write('{\n')
    names_in_data = [n for n in CONST_NAMES if n in data]
    for idx, name in enumerate(names_in_data):
        f.write(f'"{name}":')
        json.dump(data[name], f, separators=(',', ':'), ensure_ascii=False)
        if idx < len(names_in_data) - 1:
            f.write(',\n')
        else:
            f.write('\n')
    f.write('}\n')

json_size = os.path.getsize(JSON_PATH)
print(f"JSON file written: {json_size / 1024 / 1024:.1f} MB")

# Now modify the HTML
print("\nModifying HTML...")

FETCH_INIT = (
    '\n'
    '// Show loading overlay\n'
    '(function() {\n'
    '  var overlay = document.createElement("div");\n'
    '  overlay.id = "loading-overlay";\n'
    '  overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(30,30,46,0.97);display:flex;align-items:center;justify-content:center;z-index:99999;flex-direction:column;";\n'
    '  overlay.innerHTML = \'<div style="color:#e0e0e0;font-family:Inter,sans-serif;text-align:center;">\' +\n'
    '    \'<div style="font-size:2rem;margin-bottom:1rem;">Loading UK Charts Data...</div>\' +\n'
    '    \'<div style="width:200px;height:6px;background:#333;border-radius:3px;overflow:hidden;">\' +\n'
    '    \'<div id="load-bar" style="width:0%;height:100%;background:linear-gradient(90deg,#6366f1,#a78bfa);transition:width 0.3s;"></div></div>\' +\n'
    '    \'<div id="load-status" style="margin-top:0.75rem;font-size:0.9rem;color:#888;">Fetching data...</div></div>\';\n'
    '  document.body.appendChild(overlay);\n'
    '})();\n'
    '\n'
    'fetch("uk_charts_data.json")\n'
    '  .then(function(r) {\n'
    '    if (!r.ok) throw new Error("Failed to load data: " + r.status);\n'
    '    document.getElementById("load-status").textContent = "Parsing data...";\n'
    '    document.getElementById("load-bar").style.width = "60%";\n'
    '    return r.json();\n'
    '  })\n'
    '  .then(function(d) {\n'
    '    document.getElementById("load-bar").style.width = "90%";\n'
    '    document.getElementById("load-status").textContent = "Initializing...";\n'
    '\n'
    '    RAW_SONGS      = d.RAW_SONGS;\n'
    '    RAW_WEEKLY     = d.RAW_WEEKLY;\n'
    '    WEEK_INDEX     = d.WEEK_INDEX;\n'
    '    NUMBER_ONES    = d.NUMBER_ONES;\n'
    '    RAW_ALBUMS     = d.RAW_ALBUMS;\n'
    '    RAW_ALB_WEEKLY = d.RAW_ALB_WEEKLY;\n'
    '    ALB_WEEK_INDEX = d.ALB_WEEK_INDEX;\n'
    '    ALBUM_NO1S     = d.ALBUM_NO1S;\n'
    '    SONG_TRAJ      = d.SONG_TRAJ;\n'
    '    ALB_TRAJ       = d.ALB_TRAJ;\n'
    '    CHART_STATS    = d.CHART_STATS;\n'
    '    XMAS_NO1S      = d.XMAS_NO1S;\n'
    '    ONE_HIT_W      = d.ONE_HIT_W;\n'
    '    WELSH_SONGS    = d.WELSH_SONGS;\n'
    '    YEAR_CTX       = d.YEAR_CTX;\n'
    '\n'
    '    buildIndexes();\n'
    '    buildAlphaBar();\n'
    '    buildYearSelect();\n'
    '    buildAlbYearSelect();\n'
    '    renderWelcome();\n'
    '    document.getElementById("sidebar").style.display = "none";\n'
    '\n'
    '    document.getElementById("load-bar").style.width = "100%";\n'
    '    setTimeout(function() {\n'
    '      var ov = document.getElementById("loading-overlay");\n'
    '      ov.style.transition = "opacity 0.4s";\n'
    '      ov.style.opacity = "0";\n'
    '      setTimeout(function() { ov.remove(); }, 400);\n'
    '    }, 200);\n'
    '  })\n'
    '  .catch(function(err) {\n'
    '    console.error(err);\n'
    '    var s = document.getElementById("load-status");\n'
    '    if (s) { s.textContent = "Error loading data: " + err.message; s.style.color = "#f87171"; }\n'
    '  });\n'
)

new_lines = []
inserted_let_decls = False
skip_init = False

for i, line in enumerate(lines):
    # Skip lines marked for removal (data const lines)
    if i in lines_to_remove:
        if not inserted_let_decls:
            inserted_let_decls = True
            new_lines.append('// __ DATA (loaded from uk_charts_data.json) _____________________\n')
            decl_line = 'let ' + ', '.join(CONST_NAMES) + ';\n'
            new_lines.append(decl_line)
            new_lines.append('\n')
        continue

    # Skip old init body
    if skip_init:
        if line.strip() == '</script>':
            skip_init = False
            # Fall through to add </script>
        else:
            continue

    # Replace init section
    if line.strip().startswith('// \u2500\u2500 INIT '):
        new_lines.append(line)
        new_lines.append(FETCH_INIT)
        skip_init = True
        continue

    new_lines.append(line)

# Write modified HTML
print(f"Writing modified HTML ({len(new_lines)} lines)...")
with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

html_size = os.path.getsize(OUT_HTML)
orig_size = sum(len(l.encode('utf-8')) for l in lines)
print(f"\nOriginal HTML: {orig_size / 1024 / 1024:.1f} MB")
print(f"New HTML: {html_size / 1024 / 1024:.1f} MB")
print(f"JSON data: {json_size / 1024 / 1024:.1f} MB")
print(f"Size reduction: {(orig_size - html_size) / 1024 / 1024:.1f} MB removed from HTML")
print("\nDone!")

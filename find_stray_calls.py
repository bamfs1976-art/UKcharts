"""Find all standalone init calls in dist/index.html"""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "dist", "index.html")

html = open(HTML_FILE, encoding="utf-8").read()
lines = html.split('\n')

targets = ['buildIndexes()', "setMode('songs')", 'buildAlphaBar()', 
           'buildYearSelect()', 'buildAlbYearSelect()', 'renderWelcome()']

for target in targets:
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == target + ';' or stripped == target:
            print(f"Line {i+1}: {repr(line)}")
            # Show context
            for j in range(max(0,i-2), min(len(lines),i+3)):
                marker = '>>>' if j == i else '   '
                print(f"  {marker} {j+1}: {lines[j][:100]}")
            print()

import re
html = open('dist/index.html', encoding='utf-8').read()
m = re.search(r'const labels = \{[^}]+\}', html)
if m:
    print("Labels found:")
    print(m.group(0))
else:
    print("Labels NOT found!")
    # Search nearby
    idx = html.find('labels')
    if idx >= 0:
        print(f"'labels' found at {idx}:")
        print(repr(html[idx-20:idx+200]))

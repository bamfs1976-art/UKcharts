html = open('dist/index.html', encoding='utf-8').read()
lines = html.split('\n')
print(f"Total lines: {len(lines)}")
for i in range(2280, min(2295, len(lines))):
    print(f"{i+1}: {lines[i][:150]}")

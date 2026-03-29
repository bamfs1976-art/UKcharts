"""
UK Charts Data Merger v5
Run against the ORIGINAL uk_charts_complete.html only.

Usage:  python merge_chart_data.py

All four files must be in the same folder:
  uk_charts_complete.html
  uk_singles_2025_2026.csv
  uk_albums_2025_2026.csv
  merge_chart_data.py

Output: uk_charts_complete_updated.html
"""

import csv, json, re, os, sys
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
HTML_FILE   = os.path.join(SCRIPT_DIR, "uk_charts_complete.html")
SINGLES_CSV = os.path.join(SCRIPT_DIR, "uk_singles_2025_2026.csv")
ALBUMS_CSV  = os.path.join(SCRIPT_DIR, "uk_albums_2025_2026.csv")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "uk_charts_complete_updated.html")

# ---------- cleaning ---------------------------------------------------------

def clean_pos(raw):
    return raw.replace("Number","").strip()

def clean_title(raw, lw):
    t = raw.strip()
    if lw == "New" and t.startswith("New"): t = t[3:]
    elif lw == "RE"  and t.startswith("RE"):  t = t[2:]
    return t.strip()

# ---------- csv loading ------------------------------------------------------

def load_csv(path):
    chart, index = defaultdict(list), {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lw   = row["last_week"].strip()
            dstr = row["chart_date"].strip()          # "2025-08-01"
            dint = int(dstr.replace("-",""))           # 20250801
            chart[dint].append([
                clean_pos(row["position"]),
                clean_title(row["title"], lw),
                row["artist"].strip(),
                lw,
                row["peak_position"].strip(),
                row["weeks_on_chart"].strip(),
            ])
            if dstr not in index:
                dt  = datetime.strptime(dstr, "%Y-%m-%d")
                end = dt + timedelta(days=6)
                index[dt.strftime("%Y%m%d")] = (
                    f"{dt.day} {dt.strftime('%B %Y')}"
                    f"- {end.day} {end.strftime('%B %Y')}"
                )
    for k in chart:
        chart[k].sort(key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    print(f"  {os.path.basename(path)}: {len(chart)} weeks, {sum(len(v) for v in chart.values())} entries")
    return dict(chart), index

# ---------- html helpers -----------------------------------------------------

def find_bounds(html, name):
    """Return (start, end) of  const NAME = { ... };"""
    m = re.search(rf'const\s+{re.escape(name)}\s*=', html)
    if not m:
        raise ValueError(f"const {name} not found")
    depth, i, opened = 0, m.end(), False
    while i < len(html):
        c = html[i]
        if c == '{': depth += 1; opened = True
        elif c == '}':
            depth -= 1
            if opened and depth == 0:
                end = i+2 if i+1 < len(html) and html[i+1]==';' else i+1
                return m.start(), end
        i += 1
    raise ValueError(f"closing brace not found for {name}")

def inject(html, name, new_js):
    """Insert new_js before the closing brace of const NAME = {...}."""
    s, e  = find_bounds(html, name)
    block = html[s:e]
    ins   = block.rfind("}")
    before = block[:ins].rstrip()
    sep    = "\n" if before.endswith(",") else ",\n"
    return html[:s] + before + sep + new_js + "\n" + block[ins:] + html[e:]

def existing_int_keys(html, name):
    s, e = find_bounds(html, name)
    return set(int(k) for k in re.findall(r'\b(\d{8})\s*:', html[s:e]))

def existing_str_keys(html, name):
    s, e = find_bounds(html, name)
    return set(re.findall(r'"(\d{8})"', html[s:e]))

# ---------- validation -------------------------------------------------------

def validate(html, name):
    """
    Parse the constant as JSON (quoting bare integer keys first).
    Returns (ok, count, error).
    """
    try:
        s, e  = find_bounds(html, name)
        block = html[s:e]
        obj   = block[block.index('{'):]
        if obj.endswith(';'): obj = obj[:-1]
        # Quote unquoted 8-digit integer keys (valid JS, invalid JSON)
        obj = re.sub(r'(?<!["\d])(\d{8})(?=\s*:)', r'"\1"', obj)
        d = json.loads(obj)
        return True, len(d), None
    except Exception as ex:
        return False, 0, str(ex)

# ---------- inject chart data ------------------------------------------------

def inject_chart(html, name, data):
    existing = existing_int_keys(html, name)
    lines, skipped, added = [], 0, 0
    for k in sorted(data):
        if k in existing: skipped += 1; continue
        lines.append(f'{k}:{json.dumps(data[k], ensure_ascii=False, separators=(",",":"))}')
        added += 1
    print(f"    skipped {skipped}, adding {added}")
    if not lines: return html, 0
    return inject(html, name, ",\n".join(lines)), added

def inject_index(html, name, data):
    existing = existing_str_keys(html, name)
    lines, skipped, added = [], 0, 0
    for k in sorted(data):
        if k in existing: skipped += 1; continue
        lines.append(f'"{k}":"{data[k]}"')
        added += 1
    print(f"    skipped {skipped}, adding {added}")
    if not lines: return html, 0
    return inject(html, name, ",\n".join(lines)), added

# ---------- main -------------------------------------------------------------

def main():
    print("UK Charts Data Merger v5")
    print("="*50)

    for path, label in [(HTML_FILE,"HTML (original)"),(SINGLES_CSV,"Singles CSV"),(ALBUMS_CSV,"Albums CSV")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found: {path}"); sys.exit(1)
        print(f"  {label}: {os.path.basename(path)} ({os.path.getsize(path)/1e6:.1f} MB)")

    print("\nLoading CSVs...")
    sc, si = load_csv(SINGLES_CSV)
    ac, ai = load_csv(ALBUMS_CSV)

    print(f"\nReading HTML...")
    html = open(HTML_FILE, encoding="utf-8").read()
    print(f"  {len(html):,} chars")

    print("\nRAW_WEEKLY (singles):")
    html, s1 = inject_chart(html, "RAW_WEEKLY", sc)

    print("\nWEEK_INDEX (singles nav):")
    html, s2 = inject_index(html, "WEEK_INDEX", si)

    print("\nRAW_ALB_WEEKLY (albums):")
    html, a1 = inject_chart(html, "RAW_ALB_WEEKLY", ac)

    print("\nALB_WEEK_INDEX (albums nav):")
    html, a2 = inject_index(html, "ALB_WEEK_INDEX", ai)

    print("\nValidating...")
    ok = True
    for name in ("RAW_WEEKLY","WEEK_INDEX","RAW_ALB_WEEKLY","ALB_WEEK_INDEX"):
        good, count, err = validate(html, name)
        status = f"OK ({count} entries)" if good else f"FAIL — {err}"
        print(f"  {name}: {status}")
        if not good: ok = False

    if not ok:
        print("\nERROR: Validation failed — file not saved."); sys.exit(1)

    open(OUTPUT_FILE, "w", encoding="utf-8").write(html)
    size = os.path.getsize(OUTPUT_FILE)/1e6
    print(f"\nSaved: uk_charts_complete_updated.html ({size:.1f} MB)")
    print(f"\nSummary: singles +{s1} wks, index +{s2} | albums +{a1} wks, index +{a2}")

if __name__ == "__main__":
    main()

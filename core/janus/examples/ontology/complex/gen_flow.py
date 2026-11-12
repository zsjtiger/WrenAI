"""Draw the complex demo as a flowchart (SVG). Grayscale, academic-diagram style.

Steps read left to right in three rows, row by row. A person's action is drawn
with a dashed border. Run: python gen_flow.py  ->  fig_complex_demo_flow.svg
"""

from html import escape
from pathlib import Path

W, H = 960, 690
INK, MUTED, GRAY = "#1a1a1a", "#4a4a4a", "#757575"
BOX_W, BOX_H = 200, 112
XS = [28, 258, 488, 718]
ROWS = [104, 298, 492]

steps = [
    ("1 · Warehouse", "make_retail_warehouse.py", "two schemas, no declared keys", False),
    ("2 · Profile and project", "context init · duckdb profile", "project bound to the warehouse", False),
    ("3 · Draft per schema", "context draft --from-db", "10 drafts; composite keys noted", False),
    ("4 · Infer foreign keys", "context infer-fks", "tie on accounts.company_id: ambiguous", False),
    ("5 · Terms and attributes", "terms · attributes", "8 confirmed queries, 2 measures kept", False),
    ("6 · Person decides the tie", "companies, not company", "recorded in draft/relationships.yml", True),
    ("7 · Promote the drafts", "context draft apply", "any order; relationships wait for both ends", False),
    ("8 · Build and diff", "context build · diff --schema", "no drift in either schema", False),
    ("9 · Query the semantic layer", "janus --sql over MDL names", "bridge and star joins return rows", False),
    ("10 · Certify and check provenance", "certify · require_certified", "uncertified models refused at planning", False),
    ("11 · Review agent corrections", "propose · review approve|reject", "one applied, one rejected, one refused", False),
    ("12 · Failed apply", "draft apply (invalid draft)", "validation fails; models/ unchanged", False),
]
row_titles = [
    "1 · Build the candidate ontology",
    "2 · Decide and publish",
    "3 · Query, govern, and recover",
]

lines: list[str] = []
add = lines.append


def text(x, y, s, size=11, weight="400", fill=INK, anchor="start"):
    add(f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')


def box(x, y, title, cmd, outcome, human):
    dash = ' stroke-dasharray="4,3"' if human else ""
    add(f'  <rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="4" ry="4" '
        f'fill="#ffffff" stroke="{INK}" stroke-width="1.25"{dash}/>')
    cx = x + BOX_W / 2
    text(cx, y + 24, title, size=11, weight="600", anchor="middle")
    text(cx, y + 50, cmd, size=9, fill=MUTED, anchor="middle")
    text(cx, y + 78, outcome, size=9, fill=INK, anchor="middle")
    if human:
        text(cx, y + 100, "a person acts", size=8, fill=GRAY, anchor="middle")


def arrow(points):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    add(f'  <path d="{d}" fill="none" stroke="{INK}" stroke-width="1.5" '
        f'marker-end="url(#arrow)"/>')


def pos(index):
    row, col = divmod(index, 4)
    return XS[col], ROWS[row]


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add("  <style>text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }</style>")
add("  <defs>")
add('    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">')
add(f'      <polygon points="0 0, 8 3, 0 6" fill="{INK}"/>')
add("    </marker>")
add("  </defs>")
add(f'  <rect width="{W}" height="{H}" fill="#ffffff"/>')

for r, title in enumerate(row_titles):
    # start right of the return arrow, which drops down the first column
    text(XS[1], ROWS[r] - 14, title, size=10, weight="600", fill=MUTED)

for i, (title, cmd, outcome, human) in enumerate(steps):
    x, y = pos(i)
    box(x, y, title, cmd, outcome, human)

# arrows within each row (left to right)
for i in range(len(steps)):
    if i % 4 != 3 and i + 1 < len(steps):
        x1, y1 = pos(i)
        x2, _ = pos(i + 1)
        mid = y1 + BOX_H / 2
        arrow([(x1 + BOX_W, mid), (x2, mid)])

# arrows from the end of each row down to the start of the next row
for r in range(2):
    last = r * 4 + 3
    first = (r + 1) * 4
    x1, y1 = pos(last)
    x2, y2 = pos(first)
    ymid = y1 + BOX_H + (y2 - (y1 + BOX_H)) / 2
    arrow([(x1 + BOX_W / 2, y1 + BOX_H), (x1 + BOX_W / 2, ymid),
           (x2 + BOX_W / 2, ymid), (x2 + BOX_W / 2, y2)])

# legend
ly = 648
add(f'  <line x1="40" y1="{ly}" x2="72" y2="{ly}" stroke="{INK}" stroke-width="1.5" '
    f'marker-end="url(#arrow)"/>')
text(80, ly + 4, "order of steps", size=9, fill=MUTED)
add(f'  <rect x="240" y="{ly - 7}" width="28" height="14" rx="3" ry="3" fill="#ffffff" '
    f'stroke="{INK}" stroke-width="1.25" stroke-dasharray="4,3"/>')
text(278, ly + 4, "a person's decision, not automated", size=9, fill=MUTED)
text(W - 40, ly + 4, "source: run_complex_demo.sh", size=9, fill=GRAY, anchor="end")

add("</svg>")
out = Path(__file__).with_name("fig_complex_demo_flow.svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

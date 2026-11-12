"""Business-scenario flowchart for the complex ontology demo (color, Style B).

Eight scenarios, read left to right in two rows. Each names who acts, what
happens in business terms, and which demo steps show it. Colors mark the actor;
a dashed purple border marks a decision a person makes. Writes
fig_complex_demo_scenarios_color.svg.
"""

from html import escape
from pathlib import Path

W, H = 960, 570
INK, MUTED = "#1a1a1a", "#4a4a4a"
SKY, ORANGE, GREEN = "#56B4E9", "#E69F00", "#009E73"
PURPLE, VERMILLION = "#CC79A7", "#D55E00"

BOX_W, BOX_H = 200, 166
XS = [28, 254, 480, 706]
ROWS = [96, 306]

# (title lines, actor, color, story lines, demo steps, person decides)
scenarios = [
    (["Bring an existing warehouse", "into the shared model"], "Data team", SKY,
     ["Two schemas already hold the", "business data. Every table is", "drafted as a candidate model."],
     "demo steps 1–3", False),
    (["Link tables the way the", "business uses them"], "Data team", SKY,
     ["Keys are suggested from column", "names. A legacy duplicate table", "makes one link ambiguous."],
     "demo steps 4–5", False),
    (["Owner settles the ambiguous link"], "Business owner", ORANGE,
     ["The owner keeps the current", "companies table, not the legacy", "copy. Recorded for later."],
     "demo step 6", True),
    (["Publish, then confirm nothing", "has drifted from the warehouse"], "Data team", SKY,
     ["Drafts are promoted. Each schema", "is compared with the warehouse:", "no drift in either."],
     "demo steps 7–8", False),
    (["Analysts ask business questions"], "Analysts", GREEN,
     ["Revenue by category, and which", "promotions cover which products,", "run on shared business names."],
     "demo step 9", False),
    (["Finance certifies the numbers", "it signs"], "Finance", ORANGE,
     ["Core tables are certified. A query", "over uncertified tables warns; in", "strict mode it is refused."],
     "demo step 10", False),
    (["An agent proposes a fix,", "the owner decides"], "Business owner", ORANGE,
     ["The correction is queued, not", "applied. One is approved, one is", "rejected with a stated reason."],
     "demo step 11", True),
    (["A risky change is blocked"], "Change control", VERMILLION,
     ["An invalid draft fails validation", "and is rolled back. The shared", "model stays as it was."],
     "demo step 12", False),
]

lines: list[str] = []
add = lines.append


def text(x, y, s, size=11, weight="400", fill=INK, anchor="start"):
    add(f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')


def card(x, y, title, actor, color, story, ref, human):
    dash = ' stroke-dasharray="4,3"' if human else ""
    edge = PURPLE if human else color
    add(f'  <rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="4" ry="4" '
        f'fill="{color}" fill-opacity="0.12" stroke="{edge}" stroke-width="1.5"{dash}/>')
    text(x + 12, y + 22, title[0], size=11, weight="600")
    ty = 22
    for extra in title[1:]:
        ty += 15
        text(x + 12, y + ty, extra, size=11, weight="600")
    text(x + 12, y + ty + 22, actor.upper(), size=8, weight="600", fill=color if color != SKY else "#2a7fb8")
    sy = y + ty + 40
    for line in story:
        text(x + 12, sy, line, size=9, fill=INK)
        sy += 13
    text(x + 12, y + BOX_H - 12, ref, size=8, fill=MUTED)
    if human:
        text(x + BOX_W - 12, y + BOX_H - 12, "a person decides", size=8, fill=MUTED, anchor="end")


def arrow(points):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    add(f'  <path d="{d}" fill="none" stroke="{INK}" stroke-width="1.5" '
        f'marker-end="url(#arrow)"/>')


def pos(i):
    row, col = divmod(i, 4)
    return XS[col], ROWS[row]


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add("  <style>text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }</style>")
add("  <defs>")
add('    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">')
add(f'      <polygon points="0 0, 8 3, 0 6" fill="{INK}"/>')
add("    </marker>")
add("  </defs>")
add(f'  <rect width="{W}" height="{H}" fill="#ffffff"/>')

for i, (title, actor, color, story, ref, human) in enumerate(scenarios):
    x, y = pos(i)
    card(x, y, title, actor, color, story, ref, human)

for i in range(len(scenarios)):
    if i % 4 != 3 and i + 1 < len(scenarios):
        x1, y1 = pos(i)
        x2, _ = pos(i + 1)
        mid = y1 + BOX_H / 2
        arrow([(x1 + BOX_W, mid), (x2, mid)])

x1, y1 = pos(3)
x2, y2 = pos(4)
ymid = y1 + BOX_H + (y2 - (y1 + BOX_H)) / 2
arrow([(x1 + BOX_W / 2, y1 + BOX_H), (x1 + BOX_W / 2, ymid),
       (x2 + BOX_W / 2, ymid), (x2 + BOX_W / 2, y2)])

ly = 530
legend = [(SKY, "data team", 40), (ORANGE, "owner or finance", 170),
          (GREEN, "analysts", 340), (VERMILLION, "change control", 450)]
for c, label_text, lx in legend:
    add(f'  <rect x="{lx}" y="{ly - 7}" width="18" height="14" rx="3" ry="3" '
        f'fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-width="1.5"/>')
    text(lx + 24, ly + 4, label_text, size=9, fill=MUTED)
add(f'  <rect x="620" y="{ly - 7}" width="18" height="14" rx="3" ry="3" fill="#ffffff" '
    f'stroke="{PURPLE}" stroke-width="1.5" stroke-dasharray="4,3"/>')
text(644, ly + 4, "a person decides", size=9, fill=MUTED)
text(W - 40, ly + 28, "source: run_complex_demo.sh", size=9, fill=MUTED, anchor="end")

add("</svg>")
out = Path(__file__).with_name("fig_complex_demo_scenarios_color.svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

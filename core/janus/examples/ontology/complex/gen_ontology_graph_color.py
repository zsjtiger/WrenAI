"""The resulting ontology of the complex demo, as a graph (color, Style B, Chinese).

Node positions and data come from WALKTHROUGH.md: row counts from the warehouse,
certification from step 10, and the eight relationships from steps 4 and 7.
The ambiguous link is shown dashed and is not a relationship.
Writes fig_complex_demo_ontology_color_zh.svg.
"""

from html import escape
from pathlib import Path

W, H = 960, 690
INK, MUTED, GRAY = "#1a1a1a", "#4a4a4a", "#757575"
GREEN, SKY, PURPLE, ORANGE = "#009E73", "#56B4E9", "#CC79A7", "#E69F00"
BLUE = "#0072B2"
NW, NH = 150, 56

# name, center x, center y, rows, status, kind
nodes = {
    "dim_date": (100, 130, 2, "未认证", "cert"),
    "dim_store": (100, 290, 3, "已认证", "cert"),
    "dim_product": (100, 450, 4, "已认证", "cert"),
    "fact_sales": (300, 290, 5, "已认证", "cert"),
    "dim_customer": (500, 290, 3, "未认证", "plain"),
    "bridge_promo_product": (500, 450, 4, "桥接表", "bridge"),
    "dim_promo": (500, 580, 2, "未认证", "plain"),
    "accounts": (720, 290, 3, "未认证", "plain"),
    "companies": (720, 130, 2, "未认证", "plain"),
    "company": (720, 450, 2, "遗留副本，未关联", "legacy"),
}

lines: list[str] = []
add = lines.append


def text(x, y, s, size=11, weight="400", fill=INK, anchor="start"):
    add(f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')


def node(name, cx, cy, rows, status, kind):
    x, y = cx - NW / 2, cy - NH / 2
    if kind == "cert":
        fill, stroke, dash = GREEN, GREEN, ""
        fo = ' fill-opacity="0.14"'
    elif kind == "bridge":
        fill, stroke, dash = BLUE, BLUE, ""
        fo = ' fill-opacity="0.12"'
    elif kind == "legacy":
        fill, stroke, dash = GRAY, GRAY, ""
        fo = ' fill-opacity="0.08"'
    else:
        fill, stroke, dash = "#ffffff", GRAY, ""
        fo = ""
    add(f'  <rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="4" ry="4" fill="{fill}"{fo} '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
    if kind == "bridge":  # a bridge table gets a double border
        add(f'  <rect x="{x + 4}" y="{y + 4}" width="{NW - 8}" height="{NH - 8}" rx="3" ry="3" '
            f'fill="none" stroke="{BLUE}" stroke-width="1"/>')
    text(cx, y + 22, name, size=11, weight="600", anchor="middle")
    text(cx, y + 40, f"{rows} 行 · {status}", size=9, fill=MUTED, anchor="middle")


def edge(points, label=None, label_at=None, dashed=False, color=INK):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    add(f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{dash} '
        f'marker-end="url(#arrow)"/>')
    if label and label_at:
        text(label_at[0], label_at[1], label, size=8, fill=MUTED, anchor="middle")


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add("  <style>text { font-family: 'WenQuanYi Zen Hei', 'PingFang SC', 'Microsoft YaHei', sans-serif; }</style>")
add("  <defs>")
add('    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">')
add(f'      <polygon points="0 0, 8 3, 0 6" fill="{INK}"/>')
add("    </marker>")
add("  </defs>")
add(f'  <rect width="{W}" height="{H}" fill="#ffffff"/>')

# schema lanes
add(f'  <rect x="30" y="70" width="530" height="555" rx="6" ry="6" fill="#f7f7f7" stroke="#dddddd"/>')
add(f'  <rect x="600" y="70" width="335" height="420" rx="6" ry="6" fill="#f7f7f7" stroke="#dddddd"/>')
text(46, 92, "sales 销售", size=10, weight="600", fill=MUTED)
text(616, 92, "crm 客户关系", size=10, weight="600", fill=MUTED)

# relationships (child -> parent), eight in total
edge([(300, 262), (300, 200), (100, 200), (100, 158)], "date_key", (200, 192))
edge([(225, 290), (175, 290)], "store_key", (200, 280))
edge([(375, 290), (425, 290)], "customer_key", (400, 280))
edge([(575, 290), (645, 290)], "account_id", (610, 280))
edge([(720, 262), (720, 158)], "company_id", (748, 214))
edge([(300, 318), (300, 380), (100, 380), (100, 422)], "product_key", (200, 372))
edge([(425, 450), (175, 450)], "product_key", (300, 442))
edge([(500, 478), (500, 552)], "promo_id", (530, 520))

# the ambiguous link: not written, shown dashed in purple
edge([(720, 318), (720, 422)], "歧义，未写入", (748, 372), dashed=True, color=PURPLE)

for name, (cx, cy, rows, status, kind) in nodes.items():
    node(name, cx, cy, rows, status, kind)

ly = 652
legend = [("cert", "已认证"), ("plain", "未认证"), ("bridge", "桥接表"), ("legacy", "遗留副本")]
lx = 40
for kind, label_text in legend:
    if kind == "cert":
        c, fo = GREEN, "0.14"
    elif kind == "bridge":
        c, fo = BLUE, "0.12"
    elif kind == "legacy":
        c, fo = GRAY, "0.08"
    else:
        c, fo = GRAY, "0"
    add(f'  <rect x="{lx}" y="{ly - 8}" width="18" height="14" rx="3" ry="3" fill="{c}" '
        f'fill-opacity="{fo}" stroke="{c}" stroke-width="1.25"/>')
    text(lx + 24, ly + 3, label_text, size=9, fill=MUTED)
    lx += 24 + 14 * len(label_text) + 16
add(f'  <line x1="{lx}" y1="{ly}" x2="{lx + 28}" y2="{ly}" stroke="{PURPLE}" stroke-width="1.5" '
    f'stroke-dasharray="4,3"/>')
text(lx + 34, ly + 3, "歧义，未写入", size=9, fill=MUTED)
lx += 130
add(f'  <line x1="{lx}" y1="{ly}" x2="{lx + 28}" y2="{ly}" stroke="{INK}" stroke-width="1.5" '
    f'marker-end="url(#arrow)"/>')
text(lx + 34, ly + 3, "已推断的关系（多对一）", size=9, fill=MUTED)
text(W - 40, ly + 26, "来源：WALKTHROUGH.md，第 4、7、10 步", size=9, fill=GRAY, anchor="end")

add("</svg>")
out = Path(__file__).with_name("fig_complex_demo_ontology_color_zh.svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

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

import sys

ZH = "zh" in sys.argv[1:]
ZH_FONT = "'WenQuanYi Zen Hei', 'PingFang SC', 'Microsoft YaHei', sans-serif"

# Chinese text: same structure as `scenarios`, with each line kept inside the card.
zh_scenarios = [
    (["把已有仓库纳入", "共享模型"], "数据团队", SKY,
     ["两个 schema 已有业务数据，", "每张表都草拟为候选模型。"],
     "演示第 1–3 步", False),
    (["按业务实际用法", "关联表"], "数据团队", SKY,
     ["根据列名推断关联键。", "遗留的重复表让一处关联", "产生歧义。"],
     "演示第 4–5 步", False),
    (["负责人裁定有歧义的关联"], "业务负责人", ORANGE,
     ["负责人保留当前的 companies 表，", "而不是遗留副本。", "记录下来，供之后使用。"],
     "演示第 6 步", True),
    (["发布，并确认与数据仓库", "没有漂移"], "数据团队", SKY,
     ["草稿被提升。每个 schema 都与", "数据仓库比对：", "两者都没有漂移。"],
     "演示第 7–8 步", False),
    (["分析师提出业务问题"], "分析师", GREEN,
     ["按类别统计收入，以及哪些促销", "覆盖哪些产品，都基于共享的", "业务名称运行。"],
     "演示第 9 步", False),
    (["财务认证其签字的数字"], "财务", ORANGE,
     ["核心表已认证。查询未认证的表", "会给出警告；在严格模式下", "会被拒绝。"],
     "演示第 10 步", False),
    (["代理提出修正，", "由负责人决定"], "业务负责人", ORANGE,
     ["修正先排入队列，不会直接", "应用。一条获批准，一条附理由", "被驳回。"],
     "演示第 11 步", True),
    (["拦截有风险的变更"], "变更控制", VERMILLION,
     ["无效草稿校验失败并回滚，", "共享模型保持原样。"],
     "演示第 12 步", False),
]
if ZH:
    scenarios = zh_scenarios

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
        text(x + BOX_W - 12, y + BOX_H - 12, "由人决定" if ZH else "a person decides", size=8, fill=MUTED, anchor="end")


def arrow(points):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    add(f'  <path d="{d}" fill="none" stroke="{INK}" stroke-width="1.5" '
        f'marker-end="url(#arrow)"/>')


def pos(i):
    row, col = divmod(i, 4)
    return XS[col], ROWS[row]


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add("  <style>text { font-family: " + (ZH_FONT if ZH else "'Helvetica Neue', Helvetica, Arial, sans-serif") + "; }</style>")
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
legend = ([(SKY, "数据团队", 40), (ORANGE, "业务负责人或财务", 170),
           (GREEN, "分析师", 340), (VERMILLION, "变更控制", 450)] if ZH else
          [(SKY, "data team", 40), (ORANGE, "owner or finance", 170),
           (GREEN, "analysts", 340), (VERMILLION, "change control", 450)])
for c, label_text, lx in legend:
    add(f'  <rect x="{lx}" y="{ly - 7}" width="18" height="14" rx="3" ry="3" '
        f'fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-width="1.5"/>')
    text(lx + 24, ly + 4, label_text, size=9, fill=MUTED)
add(f'  <rect x="620" y="{ly - 7}" width="18" height="14" rx="3" ry="3" fill="#ffffff" '
    f'stroke="{PURPLE}" stroke-width="1.5" stroke-dasharray="4,3"/>')
text(644, ly + 4, "由人决定" if ZH else "a person decides", size=9, fill=MUTED)
text(W - 40, ly + 28, "来源：run_complex_demo.sh" if ZH else "source: run_complex_demo.sh", size=9, fill=MUTED, anchor="end")

add("</svg>")
out = Path(__file__).with_name("fig_complex_demo_scenarios_color" + ("_zh" if ZH else "") + ".svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

"""README architecture figure (Chinese), family C with icons.

Layout: three panels (callers | open context layer | data), a dashed router to a
row of four components, then the planning engine and connectors. Each card has a
small line icon drawn with SVG paths, so nothing depends on an icon font.

Colour meanings follow the figure notes: blue normal flow, purple policy and
access decisions, teal evidence and retrieval, green execution and data, amber
human review and drafts, grey dashed optional models, red refusals.

    python build_readme_architecture.py
Writes the SVG next to this file and the PNG to assets/janus-ai-architecture.zh-CN.png.
"""

from __future__ import annotations

import pathlib
from xml.sax.saxutils import escape

import cairosvg

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent.parent.parent / "assets"
W, H = 1600, 1080
FONT = "'WenQuanYi Zen Hei','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "'DejaVu Sans Mono','WenQuanYi Zen Hei',monospace"

BLUE, PURPLE, TEAL, GREEN, AMBER = "#2563eb", "#7c3aed", "#0d9488", "#16a34a", "#d97706"
RED, GREY = "#dc2626", "#6b7280"
INK, SUB, BORDER, BG, BRAND = "#1f2937", "#6b7280", "#d9dee7", "#f7f9fc", "#1E7A55"


class Svg:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def raw(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, *, fill="#ffffff", stroke=BORDER, rx=12, sw=1.2, dash=None, shadow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        f = ' filter="url(#shadow)"' if shadow else ""
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}{f}/>')

    def text(self, x, y, s, *, size=14, weight=400, fill=INK, anchor="middle", mono=False):
        font = MONO if (mono and s.isascii()) else FONT
        self.raw(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')

    def path(self, d, *, color, sw=1.8, fill="none", dash=None, arrow=False):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#arr-{color.strip("#")})"' if arrow else ""
        self.raw(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')

    def line(self, pts, *, color, sw=2, dash=None, arrow=False):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        self.path(d, color=color, sw=sw, dash=dash, arrow=arrow)

    def dot(self, cx, cy, color, r=5):
        self.raw(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def svg(self) -> str:
        colors = [BLUE, PURPLE, TEAL, GREEN, AMBER, RED, GREY]
        markers = "".join(
            f'<marker id="arr-{c.strip("#")}" markerWidth="10" markerHeight="8" refX="9" refY="4" '
            f'orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{c}"/></marker>'
            for c in colors
        )
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">'
                '<defs><filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">'
                '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.08"/>'
                f'</filter>{markers}</defs><rect width="{W}" height="{H}" fill="{BG}"/>')
        return head + "".join(self.parts) + "</svg>"


# ── icons: each draws inside a 28 x 28 box whose top-left is (x, y) ──────────

def icon(s: Svg, kind: str, x: float, y: float, color: str) -> None:
    def p(d, sw=1.8, fill="none"):
        s.path(d, color=color, sw=sw, fill=fill)

    if kind == "code":            # </>  coding agents
        p(f"M{x+9},{y+6} L{x+2},{y+14} L{x+9},{y+22}")
        p(f"M{x+19},{y+6} L{x+26},{y+14} L{x+19},{y+22}")
        p(f"M{x+16},{y+4} L{x+12},{y+24}")
    elif kind == "chat":          # speech bubble  chat assistants
        p(f"M{x+3},{y+4} H{x+25} V{y+19} H{x+12} L{x+6},{y+25} V{y+19} H{x+3} Z")
    elif kind == "apps":          # four tiles  MCP clients and apps
        for dx, dy in [(2, 2), (16, 2), (2, 16), (16, 16)]:
            p(f"M{x+dx+2},{y+dy} H{x+dx+10} V{y+dy+10} H{x+dx} V{y+dy+2} Z".replace(f"{x+dx+2}", f"{x+dx+2}"))
    elif kind == "terminal":      # >_  janus CLI / SDK
        s.rect(x + 1, y + 3, 26, 22, fill="none", stroke=color, rx=3, sw=1.8)
        p(f"M{x+6},{y+10} L{x+11},{y+14} L{x+6},{y+18}")
        p(f"M{x+14},{y+19} H{x+22}")
    elif kind == "network":       # nodes and links  MCP server / HTTP API
        for cx, cy in [(x + 14, y + 6), (x + 6, y + 22), (x + 22, y + 22)]:
            s.dot(cx, cy, color, r=3.5)
        p(f"M{x+14},{y+6} L{x+6},{y+22} M{x+14},{y+6} L{x+22},{y+22} M{x+6},{y+22} H{x+22}")
    elif kind == "chip":          # chip  janus-core-wasm
        s.rect(x + 6, y + 6, 16, 16, fill="none", stroke=color, rx=2, sw=1.8)
        for k in (10, 14, 18):
            p(f"M{x+k},{y+1} V{y+6} M{x+k},{y+22} V{y+27} M{x+1},{y+k} H{x+6} M{x+22},{y+k} H{x+27}")
    elif kind == "cube":          # cube  ontology
        p(f"M{x+14},{y+2} L{x+25},{y+8} V{y+20} L{x+14},{y+26} L{x+3},{y+20} V{y+8} Z")
        p(f"M{x+3},{y+8} L{x+14},{y+14} L{x+25},{y+8} M{x+14},{y+14} V{y+26}")
    elif kind == "book":          # open book  knowledge
        p(f"M{x+14},{y+7} C{x+10},{y+3} {x+5},{y+3} {x+2},{y+5} V{y+24} C{x+5},{y+22} {x+10},{y+22} {x+14},{y+26} Z")
        p(f"M{x+14},{y+7} C{x+18},{y+3} {x+23},{y+3} {x+26},{y+5} V{y+24} C{x+23},{y+22} {x+18},{y+22} {x+14},{y+26}")
    elif kind == "memory":        # stacked disks  memory index
        for k in (6, 13, 20):
            p(f"M{x+4},{y+k} V{y+k+4} A10,3 0 0 0 {x+24},{y+k+4} V{y+k} A10,3 0 0 0 {x+4},{y+k} Z")
    elif kind == "shield":        # shield  governed execution
        p(f"M{x+14},{y+2} L{x+25},{y+6} V{y+14} C{x+25},{y+21} {x+19},{y+25} {x+14},{y+27} "
          f"C{x+9},{y+25} {x+3},{y+21} {x+3},{y+14} V{y+6} Z")
        p(f"M{x+9},{y+14} L{x+13},{y+18} L{x+20},{y+10}")
    elif kind == "lock":          # padlock  access roles
        s.rect(x + 5, y + 12, 18, 13, fill="none", stroke=color, rx=2, sw=1.8)
        p(f"M{x+9},{y+12} V{y+8} A5,5 0 0 1 {x+19},{y+8} V{y+12}")
    elif kind == "pencil":        # document with a check  review and apply
        p(f"M{x+6},{y+2} H{x+18} L{x+24},{y+8} V{y+26} H{x+6} Z")
        p(f"M{x+10},{y+16} L{x+13},{y+20} L{x+19},{y+12}")
    elif kind == "draft":         # document lines  drafts
        p(f"M{x+6},{y+2} H{x+18} L{x+24},{y+8} V{y+26} H{x+6} Z")
        for k in (12, 16, 20):
            p(f"M{x+10},{y+k} H{x+20}")
    elif kind == "gear":          # gear  planning engine
        s.dot(x + 14, y + 14, color, r=0)
        p(f"M{x+14},{y+5} m-3,0 a3,3 0 1 0 6,0 a3,3 0 1 0 -6,0")
        p(f"M{x+14},{y+2} V{y+8} M{x+14},{y+20} V{y+26} M{x+2},{y+14} H{x+8} M{x+20},{y+14} H{x+26}")
        p(f"M{x+5},{y+5} L{x+9},{y+9} M{x+19},{y+19} L{x+23},{y+23} M{x+23},{y+5} L{x+19},{y+9} M{x+9},{y+19} L{x+5},{y+23}")
        s.raw(f'<circle cx="{x+14}" cy="{y+14}" r="7" fill="none" stroke="{color}" stroke-width="1.8"/>')
    elif kind == "plug":          # plug  connectors
        s.rect(x + 6, y + 10, 16, 14, fill="none", stroke=color, rx=3, sw=1.8)
        p(f"M{x+10},{y+10} V{y+4} M{x+18},{y+10} V{y+4} M{x+14},{y+24} V{y+28}")
    elif kind == "database":      # cylinder  warehouse
        p(f"M{x+4},{y+7} V{y+21} A10,4 0 0 0 {x+24},{y+21} V{y+7}")
        p(f"M{x+4},{y+7} A10,4 0 0 0 {x+24},{y+7} A10,4 0 0 0 {x+4},{y+7} Z")
        p(f"M{x+4},{y+14} A10,4 0 0 0 {x+24},{y+14}")
    elif kind == "audit":         # list  audit file
        s.rect(x + 5, y + 3, 18, 22, fill="none", stroke=color, rx=2, sw=1.8)
        for k in (9, 14, 19):
            p(f"M{x+9},{y+k} H{x+19}")


def card(s: Svg, x, y, w, h, title, sub, color, kind=None, *, dash=None, sw=1.4, sub_size=12):
    s.rect(x, y, w, h, stroke=color, sw=sw, dash=dash, shadow=True)
    tx = x + 16
    if kind:
        icon(s, kind, x + 14, y + (h - 28) / 2 - 2, color)
        tx = x + 52
    s.text(tx, y + h / 2 - 2, title, size=16, weight=700, anchor="start")
    s.text(tx, y + h / 2 + 18, sub, size=sub_size, fill=SUB, anchor="start")


def build() -> str:
    s = Svg()
    s.text(40, 52, "图 1 · Janus 架构", size=16, weight=700, fill=BRAND, anchor="start")
    s.text(40, 90, "面向 AI 智能体的语义层与上下文层", size=26, weight=700, anchor="start")
    s.line([(40, 110), (1560, 110)], color=BORDER, sw=1)

    # three panels, widths 320 : 760 : 360
    top, bottom = 140, 580
    pa, pb, pc = (40, 320), (400, 760), (1200, 360)

    # panel A: callers
    s.rect(pa[0], top, pa[1], bottom - top, fill="#ffffff", stroke=BORDER, rx=16)
    s.raw(f'<rect x="{pa[0]+pa[1]/2-60}" y="{top-14}" width="120" height="28" rx="14" fill="{BLUE}"/>')
    s.text(pa[0] + pa[1] / 2, top + 5, "调用方", size=14, weight=700, fill="#ffffff")
    callers = [("编码代理", "Claude Code、Cursor", "code"),
               ("聊天助手", "ChatGPT、内部助手", "chat"),
               ("MCP 客户端与应用", "CReport 应用、MCP 宿主", "apps")]
    for i, (t, sub, k) in enumerate(callers):
        card(s, pa[0] + 16, 180 + i * 130, pa[1] - 32, 96, t, sub, BLUE, k)

    # panel B: open context layer
    s.rect(pb[0], top, pb[1], bottom - top, fill="#fffbf1", stroke=AMBER, rx=16, sw=1.4, dash="6 4")
    s.raw(f'<rect x="{pb[0]+pb[1]/2-70}" y="{top-14}" width="140" height="28" rx="14" fill="{AMBER}"/>')
    s.text(pb[0] + pb[1] / 2, top + 5, "开放上下文层", size=14, weight=700, fill="#ffffff")
    s.text(pb[0] + 24, 196, "接口层：janus CLI · Python SDK · MCP 服务 · HTTP API · janus-core-wasm",
           size=13, fill=SUB, anchor="start")
    pillars = [("本体（MDL）", "模型 · 关系 · 术语", BLUE, "cube"),
               ("知识", "规则 · 枚举 · SQL 属性", GREEN, "book"),
               ("记忆", "LanceDB 混合索引", TEAL, "memory"),
               ("受治理的执行", "认证模型 · 溯源", GREEN, "shield")]
    for i, (t, sub, c, k) in enumerate(pillars):
        card(s, pb[0] + 20 + i * 185, 220, 170, 104, t, sub, c, k, sub_size=11)

    # access roles band
    s.rect(pb[0] + 20, 350, pb[1] - 40, 214, fill="#f5f0ff", stroke=PURPLE, rx=14, sw=1.6)
    icon(s, "lock", pb[0] + 40, 366, PURPLE)
    s.text(pb[0] + 76, 386, "访问角色 · 服务端定义，绑定令牌", size=15, weight=700, fill=PURPLE, anchor="start")
    steps = [("令牌", "Bearer", "lock"), ("角色", "janus_access.yml", "code"),
             ("覆盖", "允许列表", "pencil"), ("模型规则", "RLAC 行 · CLAC 列", "shield"),
             ("审计", "每次调用", "audit")]
    sw_, gap = 124, 16
    for i, (t, sub, k) in enumerate(steps):
        x = pb[0] + 40 + i * (sw_ + gap)
        s.rect(x, 404, sw_, 96, fill="#ffffff", stroke=PURPLE, rx=10, sw=1.2)
        icon(s, k, x + sw_ / 2 - 14, 412, PURPLE)
        s.text(x + sw_ / 2, 466, t, size=14, weight=700)
        s.text(x + sw_ / 2, 486, sub, size=11, fill=SUB, mono=True)
        if i < len(steps) - 1:
            s.line([(x + sw_, 452), (x + sw_ + gap, 452)], color=PURPLE, sw=1.8, arrow=True)
    s.text(pb[0] + 40, 530, "角色取值来自服务端，请求只能覆盖允许列表；固定值优先。", size=12,
           fill=INK, anchor="start")
    s.text(pb[0] + 40, 552, "被拒绝的调用同样写入审计。", size=12, fill=RED, anchor="start")

    # panel C: data
    s.rect(pc[0], top, pc[1], bottom - top, fill="#ffffff", stroke=BORDER, rx=16)
    s.raw(f'<rect x="{pc[0]+pc[1]/2-50}" y="{top-14}" width="100" height="28" rx="14" fill="{GREEN}"/>')
    s.text(pc[0] + pc[1] / 2, top + 5, "数据", size=14, weight=700, fill="#ffffff")
    card(s, pc[0] + 16, 200, pc[1] - 32, 96, "数据仓库与数据库", "数据留在原处，不复制", GREEN, "database")
    card(s, pc[0] + 16, 330, pc[1] - 32, 96, "审计文件", "令牌 · 角色 · 属性来源 · SQL", PURPLE, "audit")

    # flows between panels
    s.line([(pa[0] + pa[1], 260), (pb[0], 260)], color=BLUE, sw=2, arrow=True)
    s.line([(pb[0] + pb[1], 272), (pc[0], 248)], color=GREEN, sw=2, arrow=True)
    s.line([(pb[0] + pb[1] - 20, 470), (pc[0], 378)], color=PURPLE, sw=1.6, dash="6 4", arrow=True)

    # dashed router from panel B down to the component row
    s.line([(pb[0] + pb[1] / 2, bottom), (pb[0] + pb[1] / 2, 618)], color=GREY, sw=1.4, dash="5 4")
    comps = [("审核与应用", "代理提议 · 人工批准", AMBER, "pencil", None),
             ("草稿 draft/", "推断的外键 · 术语 · 属性", AMBER, "draft", None),
             ("嵌入模型", "冻结 · 可选", GREY, "network", "6 4"),
             ("聊天模型", "冻结 · 可选", GREY, "chat", "6 4")]
    cw, cg = 350, 40
    for i, (t, sub, c, k, d) in enumerate(comps):
        x = 40 + i * (cw + cg)
        s.line([(x + cw / 2, 618), (x + cw / 2, 648)], color=GREY, sw=1.4, dash="5 4")
        card(s, x, 648, cw, 84, t, sub, c, k, dash=d)

    # planning engine and connectors
    s.line([(40 + cw / 2, 732), (40 + cw / 2, 774)], color=BLUE, sw=2, arrow=True)
    s.text(40 + cw / 2 + 12, 758, "编译后的 MDL", size=12, fill=SUB, anchor="start")
    s.rect(40, 774, 1520, 68, fill="#eff6ff", stroke=BLUE, rx=12, sw=1.6, shadow=True)
    icon(s, "gear", 96, 794, BLUE)
    s.text(800, 802, "规划引擎：janus-core（Rust）", size=16, weight=700)
    s.text(800, 826, "MDL 展开 · CTE 改写 · 策略与访问检查", size=12, fill=SUB)
    s.line([(540, 842), (540, 884)], color=BLUE, sw=2, arrow=True)
    s.rect(40, 884, 1000, 68, fill="#eff6ff", stroke=BLUE, rx=12, sw=1.6, shadow=True)
    icon(s, "plug", 96, 904, BLUE)
    s.text(580, 912, "连接器", size=16, weight=700)
    s.text(580, 936, "20 个数据源 · 各方言 SQL", size=12, fill=SUB)
    s.line([(1040, 918), (1200, 918)], color=GREEN, sw=2.2, arrow=True)
    s.rect(1200, 884, 360, 68, fill="#f0fdf4", stroke=GREEN, rx=12, sw=1.6, shadow=True)
    icon(s, "database", 1256, 904, GREEN)
    s.text(1420, 912, "数据仓库与数据库", size=16, weight=700)
    s.text(1420, 936, "数据留在原处", size=12, fill=SUB)

    # legend
    s.text(40, 1000, "图例", size=13, weight=700, anchor="start")
    legend = [(100, BLUE, "查询与数据流"), (240, PURPLE, "访问决策"), (370, AMBER, "人工审核"),
              (500, GREEN, "执行与数据"), (630, GREY, "可选的冻结模型"), (790, RED, "被拒绝的调用")]
    for x, c, label in legend:
        s.raw(f'<rect x="{x}" y="988" width="18" height="14" rx="3" fill="#ffffff" stroke="{c}" stroke-width="1.6"/>')
        s.text(x + 26, 1000, label, size=12, fill=SUB, anchor="start")
    s.line([(40, 1030), (1560, 1030)], color=BORDER, sw=1)
    s.text(40, 1054, "Janus · 架构图", size=12, fill=SUB, anchor="start")
    return s.svg()


def main() -> None:
    svg = build()
    (HERE / "janus-architecture.zh-CN.svg").write_text(svg, encoding="utf-8")
    ASSETS.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                     write_to=str(ASSETS / "janus-ai-architecture.zh-CN.png"),
                     output_width=W * 2)
    print("wrote", HERE / "janus-architecture.zh-CN.svg", "and", ASSETS / "janus-ai-architecture.zh-CN.png")


if __name__ == "__main__":
    main()

"""Janus architecture, drawn as a multi-panel architecture figure (family C).

Layout: three panels (callers | open context layer | data), a dashed router
down to a row of four components, then the planning engine and connectors.

Colour meanings are fixed (see docs/... process notes):
  blue    normal flow, planning and connectors
  purple  policy and access decisions (the role band)
  teal    evidence and retrieval (memory)
  green   governed execution and final data
  amber   human review and drafts
  grey    optional frozen models (dashed)
  red     refused requests

Writes janus-architecture-infographic.zh-CN.svg and .png next to this file.
    python build_infographic.py
"""

from __future__ import annotations

import pathlib
from xml.sax.saxutils import escape

import cairosvg

HERE = pathlib.Path(__file__).resolve().parent
W, H = 1600, 1000
FONT = "'WenQuanYi Zen Hei','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "'DejaVu Sans Mono','WenQuanYi Zen Hei',monospace"

BLUE, PURPLE, TEAL, GREEN, AMBER = "#2563eb", "#7c3aed", "#0d9488", "#16a34a", "#d97706"
RED, GREY = "#dc2626", "#6b7280"
INK, SUB, BORDER, BG = "#1f2937", "#6b7280", "#d9dee7", "#f7f9fc"
BRAND = "#1E7A55"


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
        # monospace only for plain ASCII; Chinese text uses the CJK sans stack
        font = MONO if (mono and s.isascii()) else FONT
        self.raw(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')

    def line(self, pts, *, color=BLUE, sw=2, dash=None, arrow=False):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arr-%s)"' % color.strip("#") if arrow else ""
        self.raw(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{m}/>')

    def dot(self, cx, cy, color, r=5):
        self.raw(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')

    def tag(self, cx, y, label, color, w=None):
        w = w or (len(label) * 15 + 28)
        self.rect(cx - w / 2, y, w, 28, fill=color, stroke=color, rx=14, sw=0)
        self.text(cx, y + 19, label, size=14, weight=700, fill="#ffffff")

    def svg(self) -> str:
        colors = [BLUE, PURPLE, RED, GREEN, TEAL, AMBER, GREY]
        markers = "".join(
            f'<marker id="arr-{c.strip("#")}" markerWidth="10" markerHeight="8" refX="9" refY="4" '
            f'orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{c}"/></marker>'
            for c in colors
        )
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">'
                '<defs><filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">'
                '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" '
                'flood-opacity="0.08"/></filter>'
                f"{markers}</defs>"
                f'<rect width="{W}" height="{H}" fill="{BG}"/>')
        return head + "".join(self.parts) + "</svg>"


def card(s: Svg, x, y, w, h, title, sub, color, *, dash=None, sw=1.2):
    s.rect(x, y, w, h, stroke=color, sw=sw, dash=dash, shadow=True)
    s.dot(x + 16, y + 22, color, r=5)
    s.text(x + 30, y + 27, title, size=16, weight=700, anchor="start")
    s.text(x + 30, y + 49, sub, size=13, fill=SUB, anchor="start")


def build() -> str:
    s = Svg()

    # caption block (book conventions: figure number in brand green, title below)
    s.text(40, 52, "图 1 · Janus 架构", size=16, weight=700, fill=BRAND, anchor="start")
    s.text(40, 90, "从提问到数据的受控路径", size=26, weight=700, anchor="start")
    s.line([(40, 110), (1560, 110)], color=BORDER, sw=1)

    # three panels, widths 320 : 760 : 360
    pa, pb, pc = (40, 140, 320), (400, 140, 760), (1200, 140, 360)
    top, bottom = 140, 560

    # panel A: callers
    s.rect(pa[0], top, pa[2], bottom - top, fill="#ffffff", stroke=BORDER, rx=16)
    s.tag(pa[0] + pa[2] / 2, top - 14, "调用方", BLUE, w=120)
    callers = [("编码代理", "Claude Code · Cursor"), ("聊天助手", "ChatGPT · 内部助手"),
               ("MCP 客户端与应用", "CReport 应用 · MCP 宿主")]
    for i, (t, sub) in enumerate(callers):
        card(s, pa[0] + 20, 190 + i * 110, pa[2] - 40, 80, t, sub, BLUE)

    # panel B: open context layer
    s.rect(pb[0], top, pb[2], bottom - top, fill="#fffbf1", stroke=AMBER, rx=16, sw=1.4, dash="6 4")
    s.tag(pb[0] + pb[2] / 2, top - 14, "开放上下文层", AMBER, w=170)
    s.text(pb[0] + 24, 200, "本项目的核心，全部可审阅、可版本管理", size=13, fill=SUB, anchor="start")
    pillars = [("本体（MDL）", "模型 · 关系 · 术语", BLUE), ("知识", "规则 · 枚举 · SQL 属性", GREEN),
               ("记忆", "召回已确认的 NL→SQL", TEAL), ("受治理的执行", "认证模型 · 溯源", GREEN)]
    for i, (t, sub, c) in enumerate(pillars):
        x = pb[0] + 20 + i * 185
        card(s, x, 220, 170, 92, t, sub, c)

    # the role band (policy and access decisions: purple)
    s.rect(pb[0] + 20, 340, pb[2] - 40, 200, fill="#f5f0ff", stroke=PURPLE, rx=14, sw=1.6)
    s.text(pb[0] + 40, 368, "访问角色 · 服务端定义，绑定令牌", size=15, weight=700, fill=PURPLE, anchor="start")
    steps = [("令牌", "Bearer"), ("角色", "janus_access.yml"), ("覆盖", "允许列表"),
             ("模型规则", "RLAC 行 · CLAC 列"), ("审计", "每次调用")]
    sw_, gap = 124, 16
    for i, (t, sub) in enumerate(steps):
        x = pb[0] + 40 + i * (sw_ + gap)
        s.rect(x, 390, sw_, 80, fill="#ffffff", stroke=PURPLE, rx=10, sw=1.2)
        s.text(x + sw_ / 2, 418, t, size=14, weight=700)
        s.text(x + sw_ / 2, 440, sub, size=11, fill=SUB, mono=True)
        if i < len(steps) - 1:
            s.line([(x + sw_, 430), (x + sw_ + gap, 430)], color=PURPLE, sw=1.8, arrow=True)
    s.text(pb[0] + 40, 500, "角色取值来自服务端，请求只能覆盖允许列表；固定值优先。", size=12,
           fill=INK, anchor="start")
    s.text(pb[0] + 40, 524, "被拒绝的调用同样写入审计。", size=12, fill=RED, anchor="start")

    # panel C: data
    s.rect(pc[0], top, pc[2], bottom - top, fill="#ffffff", stroke=BORDER, rx=16)
    s.tag(pc[0] + pc[2] / 2, top - 14, "数据", GREEN, w=100)
    card(s, pc[0] + 20, 190, pc[2] - 40, 92, "数据仓库与数据库", "数据留在原处，不复制", GREEN)
    card(s, pc[0] + 20, 320, pc[2] - 40, 92, "审计文件", "令牌 · 角色 · 属性来源 · SQL", PURPLE)

    # flows between panels
    s.line([(pa[0] + pa[2], 300), (pb[0], 300)], color=BLUE, sw=2, arrow=True)
    s.line([(pb[0] + pb[2], 266), (pc[0], 236)], color=GREEN, sw=2, arrow=True)
    s.line([(pb[0] + pb[2] - 20, 440), (pc[0], 366)], color=PURPLE, sw=1.6, dash="6 4", arrow=True)

    # dashed router from panel B down to the component row
    s.line([(pb[0] + pb[2] / 2, bottom), (pb[0] + pb[2] / 2, 580)], color=GREY, sw=1.4, dash="5 4")
    comps = [("审核与应用", "代理提议 · 人工批准", AMBER, None),
             ("草稿 draft/", "推断的外键 · 术语 · 属性", AMBER, None),
             ("嵌入模型", "冻结 · 可选", GREY, "6 4"),
             ("聊天模型", "冻结 · 可选", GREY, "6 4")]
    cw, cg = 350, 40
    for i, (t, sub, c, d) in enumerate(comps):
        x = 40 + i * (cw + cg)
        s.line([(x + cw / 2, 580), (x + cw / 2, 610)], color=GREY, sw=1.4, dash="5 4")
        card(s, x, 610, cw, 74, t, sub, c, dash=d)

    # planning engine and connectors
    s.line([(40 + cw / 2, 684), (40 + cw / 2, 730)], color=BLUE, sw=2, arrow=True)
    s.text(40 + cw / 2 + 12, 712, "编译后的 MDL", size=12, fill=SUB, anchor="start")
    s.rect(40, 730, 1520, 60, fill="#eff6ff", stroke=BLUE, rx=12, sw=1.6, shadow=True)
    s.text(800, 758, "规划引擎：janus-core（Rust）", size=16, weight=700)
    s.text(800, 780, "MDL 展开 · CTE 改写 · 策略与访问检查", size=12, fill=SUB)
    s.line([(540, 790), (540, 826)], color=BLUE, sw=2, arrow=True)
    s.rect(40, 826, 1000, 60, fill="#eff6ff", stroke=BLUE, rx=12, sw=1.6, shadow=True)
    s.text(540, 854, "连接器", size=16, weight=700)
    s.text(540, 876, "20 个数据源 · 各方言 SQL", size=12, fill=SUB)
    s.line([(1040, 856), (1200, 856)], color=GREEN, sw=2.2, arrow=True)
    s.rect(1200, 826, 360, 60, fill="#f0fdf4", stroke=GREEN, rx=12, sw=1.6, shadow=True)
    s.text(1380, 854, "数据仓库与数据库", size=16, weight=700)

    # legend
    s.text(40, 926, "图例", size=13, weight=700, anchor="start")
    legend = [(90, BLUE, "查询与数据流"), (250, PURPLE, "访问决策"), (380, AMBER, "人工审核"),
              (500, GREEN, "执行与数据"), (630, GREY, "可选的冻结模型"), (790, RED, "被拒绝的调用")]
    for x, c, label in legend:
        s.rect(x, 912, 18, 14, fill="#ffffff", stroke=c, rx=3, sw=1.6)
        s.text(x + 26, 924, label, size=12, fill=SUB, anchor="start")

    s.line([(40, 952), (1560, 952)], color=BORDER, sw=1)
    s.text(40, 976, "Janus · 架构图", size=12, fill=SUB, anchor="start")
    s.text(1560, 976, "1 / 1", size=12, fill=SUB, anchor="end")
    return s.svg()


def main() -> None:
    svg = build()
    out = HERE / "janus-architecture-infographic.zh-CN"
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out.with_suffix(".png")),
                     output_width=W * 2)
    print("wrote", out.with_suffix(".svg"), "and", out.with_suffix(".png"))


if __name__ == "__main__":
    main()

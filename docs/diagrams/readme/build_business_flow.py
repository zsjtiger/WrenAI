"""Business flow: the same data, different views by role (family D, lifecycle with branches).

Top: one request, six steps, with the refusal branches under the steps they come from.
Bottom: one source table feeding two views, the analyst's and the manager's.

Colours (fixed meanings, as in the other Janus figures):
  blue    normal flow
  purple  policy and access decisions
  green   data returned to a caller
  red     refused requests
  grey    the data source and notes

Writes business-flow.zh-CN.svg and .png next to this file.
    python build_business_flow.py
"""

from __future__ import annotations

import pathlib
from xml.sax.saxutils import escape

import cairosvg

HERE = pathlib.Path(__file__).resolve().parent
W, H = 1600, 1000
FONT = "'WenQuanYi Zen Hei','Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "'DejaVu Sans Mono','WenQuanYi Zen Hei',monospace"

BLUE, PURPLE, GREEN, RED, GREY, AMBER = "#2563eb", "#7c3aed", "#16a34a", "#dc2626", "#6b7280", "#d97706"
INK, SUB, BORDER, BG, BRAND = "#1f2937", "#6b7280", "#d9dee7", "#f7f9fc", "#1E7A55"


class Svg:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, *, fill="#ffffff", stroke=BORDER, rx=12, sw=1.2, dash=None, shadow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        f = ' filter="url(#shadow)"' if shadow else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}{f}/>')

    def text(self, x, y, s, *, size=14, weight=400, fill=INK, anchor="middle", mono=False):
        font = MONO if (mono and s.isascii()) else FONT
        self.add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')

    def path(self, pts, *, color=BLUE, sw=2, dash=None, arrow=False):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#arr-{color.strip("#")})"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{m}/>')

    def svg(self) -> str:
        colors = [BLUE, PURPLE, GREEN, RED, GREY]
        markers = "".join(
            f'<marker id="arr-{c.strip("#")}" markerWidth="10" markerHeight="8" refX="9" refY="4" '
            f'orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{c}"/></marker>'
            for c in colors
        )
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                '<defs><filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">'
                '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.08"/>'
                f'</filter>{markers}</defs><rect width="{W}" height="{H}" fill="{BG}"/>')
        return head + "".join(self.parts) + "</svg>"


def step_card(s: Svg, x, y, w, h, num, title, sub, color, *, dash=None):
    s.rect(x, y, w, h, stroke=color, sw=1.6, dash=dash, shadow=True)
    s.rect(x + w / 2 - 14, y - 14, 28, 28, fill=color, stroke=color, rx=14, sw=0)
    s.text(x + w / 2, y + 5, str(num), size=14, weight=700, fill="#ffffff")
    s.text(x + w / 2, y + 36, title, size=16, weight=700)
    s.text(x + w / 2, y + 58, sub, size=12, fill=SUB)


def refusal(s: Svg, x, y, w, title, sub):
    s.rect(x, y, w, 66, fill="#fef2f2", stroke=RED, rx=10, sw=1.4)
    s.text(x + w / 2, y + 26, title, size=14, weight=700, fill=RED)
    s.text(x + w / 2, y + 48, sub, size=12, fill=SUB)


def build() -> str:
    s = Svg()

    # caption block
    s.text(40, 52, "图 2 · 业务流程", size=16, weight=700, fill=BRAND, anchor="start")
    s.text(40, 90, "同一份数据，不同的人看到不同的内容", size=26, weight=700, anchor="start")
    s.add(f'<line x1="40" y1="110" x2="1560" y2="110" stroke="{BORDER}" stroke-width="1"/>')

    # main path: six steps across the top
    steps = [
        ("业务人员提问", "自然语言或 SQL", BLUE),
        ("带令牌请求", "Authorization: Bearer", BLUE),
        ("识别角色", "令牌绑定默认角色", PURPLE),
        ("检查覆盖", "允许列表与固定值", PURPLE),
        ("规划并过滤", "行规则 · 列规则", PURPLE),
        ("返回结果", "并写入审计", GREEN),
    ]
    sw_, gap, x0, y0 = 220, 32, 60, 200
    for i, (t, sub, c) in enumerate(steps):
        x = x0 + i * (sw_ + gap)
        step_card(s, x, y0, sw_, 90, i + 1, t, sub, c)
        if i < len(steps) - 1:
            s.path([(x + sw_, y0 + 45), (x + sw_ + gap, y0 + 45)], color=BLUE, sw=2, arrow=True)

    # refusal branches, under the steps they come from
    def x_of(i):
        return x0 + i * (sw_ + gap)

    refusal(s, x_of(1) - 20, 370, 260, "无有效令牌 → 401", "请求在到达引擎前被拒绝")
    s.path([(x_of(1) + sw_ / 2, y0 + 90), (x_of(1) + sw_ / 2, 370)], color=RED, sw=1.6, dash="6 4", arrow=True)
    # each refusal sits under the step it comes from, centred on that step
    c3 = x_of(3) + sw_ / 2
    refusal(s, c3 - 115, 370, 230, "越权覆盖或选角色 → 403", "不在允许列表，或令牌无权")
    s.path([(c3, y0 + 90), (c3, 370)], color=RED, sw=1.6, dash="6 4", arrow=True)
    c4 = x_of(4) + sw_ / 2
    refusal(s, c4 - 125, 370, 250, "查询含无权列 → 422", "Permission Denied，整条查询失败")
    s.path([(c4, y0 + 90), (c4, 370)], color=RED, sw=1.6, dash="6 4", arrow=True)

    # bottom: one source, two views
    s.text(800, 490, "同一份数据，按角色得到不同视图", size=16, weight=700, fill=INK)
    s.rect(60, 540, 300, 180, fill="#ffffff", stroke=GREY, rx=14, sw=1.4, dash="6 4", shadow=True)
    s.text(210, 580, "orders 表", size=18, weight=700)
    s.text(210, 606, "6 行订单", size=13, fill=SUB)
    s.text(210, 640, "customer_id · amount", size=12, fill=SUB, mono=True)
    s.text(210, 662, "status", size=12, fill=SUB, mono=True)
    s.text(210, 694, "数据只有一份，不复制", size=12, fill=INK)

    # arrows from the source to the two panels
    s.path([(360, 610), (420, 610), (420, 590), (480, 590)], color=GREY, sw=1.6, arrow=True)
    s.path([(360, 650), (420, 650), (420, 700), (480, 700)], color=GREY, sw=1.6, arrow=True)

    # analyst panel
    ax, ay, aw, ah = 480, 540, 500, 260
    s.rect(ax, ay, aw, ah, fill="#ffffff", stroke=BLUE, rx=14, sw=1.6, shadow=True)
    s.text(ax + 24, ay + 34, "分析师视图", size=18, weight=700, fill=BLUE, anchor="start")
    s.text(ax + 24, ay + 58, "角色 analyst · session_level = 1 · 只看自己的客户", size=12, fill=SUB, anchor="start")
    s.rect(ax + 24, ay + 74, aw - 48, 30, fill="#eef2f7", stroke="none", rx=6, sw=0)
    for cx, label in [(ax + 60, "订单号"), (ax + 220, "客户"), (ax + 380, "金额")]:
        s.text(cx, ay + 94, label, size=13, weight=700)
    rows = [("101", "1", "受限"), ("102", "1", "受限")]
    for i, (oid, cust, amt) in enumerate(rows):
        yy = ay + 128 + i * 32
        s.text(ax + 60, yy, oid, size=14, mono=True)
        s.text(ax + 220, yy, cust, size=14, mono=True)
        s.text(ax + 380, yy, amt, size=13, fill=RED)
    s.text(ax + 24, ay + 218, "金额列被拒绝；只查 order_id 与客户即可执行", size=12, fill=RED, anchor="start")
    s.text(ax + 24, ay + 240, "其他客户的订单不会出现", size=12, fill=SUB, anchor="start")

    # manager panel
    mx, my, mw, mh = 1020, 540, 520, 260
    s.rect(mx, my, mw, mh, fill="#ffffff", stroke=GREEN, rx=14, sw=1.6, shadow=True)
    s.text(mx + 24, my + 34, "经理视图", size=18, weight=700, fill=GREEN, anchor="start")
    s.text(mx + 24, my + 58, "角色 manager · session_level = 3 · 全部订单", size=12, fill=SUB, anchor="start")
    s.rect(mx + 24, my + 74, mw - 48, 30, fill="#eef2f7", stroke="none", rx=6, sw=0)
    for cx, label in [(mx + 50, "订单号"), (mx + 200, "客户"), (mx + 350, "金额")]:
        s.text(cx, my + 94, label, size=13, weight=700)
    data = [("101", "1", "120.00"), ("102", "1", "35.50"), ("103", "2", "480.00"),
            ("104", "3", "75.25"), ("105", "4", "210.00"), ("106", "2", "18.90")]
    for i, (oid, cust, amt) in enumerate(data):
        yy = my + 118 + i * 20
        s.text(mx + 50, yy, oid, size=12, mono=True)
        s.text(mx + 200, yy, cust, size=12, mono=True)
        s.text(mx + 350, yy, amt, size=12, mono=True, fill=GREEN)
    s.text(mx + 24, my + 248, "6 条订单全部可见，金额可见", size=12, fill=GREEN, anchor="start")

    # legend
    s.text(60, 866, "图例", size=13, weight=700, anchor="start")
    legend = [(120, BLUE, "正常流程"), (260, PURPLE, "访问决策"), (400, GREEN, "返回给调用方"),
              (560, RED, "被拒绝的调用"), (720, GREY, "数据来源")]
    for x, c, label in legend:
        s.rect(x, 854, 18, 14, fill="#ffffff", stroke=c, rx=3, sw=1.6)
        s.text(x + 26, 866, label, size=12, fill=SUB, anchor="start")

    s.add(f'<line x1="40" y1="952" x2="1560" y2="952" stroke="{BORDER}" stroke-width="1"/>')
    s.text(40, 976, "Janus · 业务流程", size=12, fill=SUB, anchor="start")
    s.text(1560, 976, "2 / 2", size=12, fill=SUB, anchor="end")
    return s.svg()


def main() -> None:
    svg = build()
    out = HERE / "business-flow.zh-CN"
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out.with_suffix(".png")),
                     output_width=W * 2)
    print("wrote", out.with_suffix(".svg"), "and", out.with_suffix(".png"))


if __name__ == "__main__":
    main()

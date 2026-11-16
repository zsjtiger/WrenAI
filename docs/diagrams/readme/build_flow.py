"""Homepage architecture figure, in the layout of the README flowchart, with roles.

Writes the English and Chinese figures as SVG (source, kept here) and PNG
(shown by the READMEs, written to assets/):

    python build_flow.py

The layout is the same in both languages. Only the labels change.
"""

from __future__ import annotations

import pathlib
from xml.sax.saxutils import escape

import cairosvg

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent.parent.parent / "assets"
W, H = 1400, 1260
FONT = "'WenQuanYi Zen Hei','Noto Sans CJK SC','Helvetica Neue',Arial,sans-serif"

CLIENT = ("#e8f4fd", "#5aa0d6")  # external clients
SYSTEM = ("#dbeaf5", "#3b7bbf")  # system components
OPEN = ("#fdf3dc", "#e8b04b")  # this project's open context layer
EXEC = ("#f8e6c2", "#d89a2b")  # governed execution
DATA = ("#e3f5ea", "#3c9a68")  # data and drafts
OPT = ("#fbe9f1", "#c46b9b")  # optional frozen models
ROLE = ("#eef3ff", "#2f5bea")  # access roles (new)
INK, MUTE = "#1f2a37", "#5b6675"

TEXT = {
    "en": {
        "clients": "Coding agents", "clients_s": "Claude Code · Cursor",
        "chat": "Chat assistants", "chat_s": "ChatGPT · internal copilots",
        "apps": "MCP clients & apps", "apps_s": "CReport app · MCP hosts",
        "iface1": "janus CLI · Python SDK", "iface1_s": "query, context, memory",
        "iface2": "MCP server · HTTP API", "iface2_s": "tools and endpoints",
        "iface3": "janus-core-wasm", "iface3_s": "in-browser planning",
        "layer": "Open context layer", "layer_s": "Governed CReport from context you can read, diff, and own.",
        "ont": "Ontology (MDL)", "ont_s": "models · relationships · terms",
        "know": "Knowledge", "know_s": "rules · enums · mined SQL attributes",
        "mem": "Memory", "mem_s": "LanceDB hybrid index · recall of NL→SQL",
        "exec": "Governed execution", "exec_s": "certified models · provenance · dry-plan",
        "role_title": "Access roles · server-side, token-bound",
        "tok": "Token", "tok_s": "Authorization: Bearer",
        "role": "Role", "role_s": "janus_access.yml · one-row SQL",
        "ovr": "Overrides", "ovr_s": "allow list only",
        "rules": "Model rules", "rules_s": "RLAC rows · CLAC columns",
        "audit": "Audit", "audit_s": "every call, incl. refused",
        "role_note": "Role values come from the server, never the client. Requests may override only the allow list; fixed values win.",
        "review": "Review & apply", "review_s": "agent proposes · human approves",
        "draft": "Draft (draft/)", "draft_s": "inferred keys · terms · attributes",
        "embed": "Embedding model", "embed_s": "frozen · optional",
        "chatm": "Chat model", "chatm_s": "frozen · optional",
        "plan": "Planning engine: janus-core (Rust)", "plan_s": "MDL expansion · CTE rewrite · policy and access checks",
        "conn": "Connectors", "conn_s": "20 data sources · dialect-specific SQL",
        "wh": "Warehouses & databases", "wh_s": "your data stays where it is",
        "compiled": "compiled MDL", "suggest": "suggest",
        "legend": "Legend", "l_client": "External clients", "l_system": "System components",
        "l_open": "This project's open layer", "l_data": "Data and drafts",
        "l_opt": "Optional frozen model", "l_role": "Access roles (new)",
        "l_flow": "query and data flow", "l_opt_flow": "optional model call",
    },
    "zh-CN": {
        "clients": "编码代理", "clients_s": "Claude Code、Cursor",
        "chat": "聊天助手", "chat_s": "ChatGPT、内部助手",
        "apps": "MCP 客户端与应用", "apps_s": "CReport 应用、MCP 宿主",
        "iface1": "janus CLI · Python SDK", "iface1_s": "查询、上下文、记忆",
        "iface2": "MCP 服务 · HTTP API", "iface2_s": "工具与接口",
        "iface3": "janus-core-wasm", "iface3_s": "浏览器内规划",
        "layer": "开放上下文层", "layer_s": "受治理的 CReport：上下文可读、可比对、可掌控。",
        "ont": "本体（MDL）", "ont_s": "模型 · 关系 · 术语",
        "know": "知识", "know_s": "规则 · 枚举 · 挖掘出的 SQL 属性",
        "mem": "记忆", "mem_s": "LanceDB 混合索引 · 召回 NL→SQL",
        "exec": "受治理的执行", "exec_s": "认证模型 · 溯源 · dry-plan",
        "role_title": "访问角色 · 服务端定义，绑定令牌",
        "tok": "令牌", "tok_s": "Authorization: Bearer",
        "role": "角色", "role_s": "janus_access.yml · 单行 SQL",
        "ovr": "覆盖", "ovr_s": "仅限允许列表",
        "rules": "模型规则", "rules_s": "RLAC 行 · CLAC 列",
        "audit": "审计", "audit_s": "每次调用，含被拒绝的",
        "role_note": "角色取值来自服务端，不来自客户端。请求只能覆盖允许列表；固定值优先。",
        "review": "审核与应用", "review_s": "代理提议 · 人工批准",
        "draft": "草稿（draft/）", "draft_s": "推断的外键 · 术语 · 属性",
        "embed": "嵌入模型", "embed_s": "冻结 · 可选",
        "chatm": "聊天模型", "chatm_s": "冻结 · 可选",
        "plan": "规划引擎：janus-core（Rust）", "plan_s": "MDL 展开 · CTE 改写 · 策略与访问检查",
        "conn": "连接器", "conn_s": "20 个数据源 · 各方言 SQL",
        "wh": "数据仓库与数据库", "wh_s": "数据留在原处",
        "compiled": "编译后的 MDL", "suggest": "建议",
        "legend": "图例", "l_client": "外部客户端", "l_system": "系统组件",
        "l_open": "本项目的开放上下文层", "l_data": "数据与草稿",
        "l_opt": "可选的冻结模型", "l_role": "访问角色（新增）",
        "l_flow": "查询与数据流", "l_opt_flow": "可选的模型调用",
    },
}


class Canvas:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def box(self, x, y, w, h, colors, *, r=10, dashed=False, stroke_w=1.6):
        fill, stroke = colors
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{stroke_w}"{dash}/>')

    def text(self, x, y, s, *, size=14, weight=400, fill=INK, anchor="middle"):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-family="{FONT}">{escape(s)}</text>')

    def arrow(self, x1, y1, x2, y2, *, color=MUTE, dashed=False, width=1.6):
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{width}"{dash} marker-end="url(#arrow)"/>')

    def svg(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">'
                '<defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" '
                'orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#5b6675"/></marker></defs>'
                f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
        return head + "".join(self.parts) + "</svg>"


def build(lang: str) -> str:
    t = TEXT[lang]
    c = Canvas()

    # row 1: who sends requests
    top = [(40, "clients", "clients_s"), (490, "chat", "chat_s"), (940, "apps", "apps_s")]
    for x, k, ks in top:
        c.box(x, 40, 420, 70, CLIENT)
        c.text(x + 210, 70, t[k], size=18, weight=700)
        c.text(x + 210, 94, t[ks], size=13, fill=MUTE)
        c.arrow(x + 210, 110, x + 210, 170)

    # row 2: entry points
    iface = [(40, "iface1", "iface1_s"), (490, "iface2", "iface2_s"), (940, "iface3", "iface3_s")]
    for x, k, ks in iface:
        c.box(x, 170, 420, 62, SYSTEM)
        c.text(x + 210, 196, t[k], size=16, weight=700)
        c.text(x + 210, 218, t[ks], size=13, fill=MUTE)
        c.arrow(x + 210, 232, x + 210, 286)

    # the open context layer, with the role band inside it
    c.box(30, 286, 1340, 410, OPEN, r=14, dashed=True, stroke_w=1.4)
    c.text(60, 316, t["layer"], size=22, weight=700, anchor="start")
    c.text(60, 340, t["layer_s"], size=13, fill=MUTE, anchor="start")
    pillars = [(60, "ont", "ont_s"), (370, "know", "know_s"), (680, "mem", "mem_s"), (990, "exec", "exec_s")]
    for x, k, ks in pillars:
        colors = EXEC if k == "exec" else OPEN
        c.box(x, 356, 290, 92, colors if k == "exec" else ("#ffffff", OPEN[1]))
        c.text(x + 145, 390, t[k], size=17, weight=700)
        c.text(x + 145, 414, t[ks], size=12, fill=MUTE)

    # the role band (new)
    c.box(60, 470, 1280, 210, ROLE, r=12, stroke_w=2)
    c.text(90, 500, t["role_title"], size=16, weight=700, anchor="start", fill=ROLE[1])
    steps = [
        (90, "tok", "tok_s"), (330, "role", "role_s"), (570, "ovr", "ovr_s"),
        (810, "rules", "rules_s"), (1050, "audit", "audit_s"),
    ]
    for x, k, ks in steps:
        hot = k == "role"
        c.box(x, 520, 220, 96, ("#ffffff", ROLE[1]), r=8, stroke_w=2 if hot else 1.2)
        c.text(x + 110, 550, t[k], size=16, weight=700)
        c.text(x + 110, 574, t[ks], size=12, fill=MUTE)
        if k != "audit":
            nx = steps[steps.index((x, k, ks)) + 1][0]
            c.arrow(x + 220, 568, nx, 568, color=ROLE[1], width=1.8)
    c.text(90, 650, t["role_note"], size=13, fill=INK, anchor="start")

    # review, drafts, optional models
    c.arrow(330, 696, 330, 716, color=MUTE)
    c.box(60, 716, 300, 66, DATA)
    c.text(210, 744, t["review"], size=15, weight=700)
    c.text(210, 766, t["review_s"], size=12, fill=MUTE)
    c.box(400, 716, 300, 66, DATA)
    c.text(550, 744, t["draft"], size=15, weight=700)
    c.text(550, 766, t["draft_s"], size=12, fill=MUTE)
    c.arrow(400, 749, 360, 749, color=MUTE)
    c.text(380, 740, t["suggest"], size=11, fill=MUTE)
    c.box(740, 716, 300, 66, OPT, dashed=True)
    c.text(890, 744, t["embed"], size=15, weight=700)
    c.text(890, 766, t["embed_s"], size=12, fill=MUTE)
    c.box(1080, 716, 280, 66, OPT, dashed=True)
    c.text(1220, 744, t["chatm"], size=15, weight=700)
    c.text(1220, 766, t["chatm_s"], size=12, fill=MUTE)
    c.arrow(890, 716, 890, 696, color=OPT[1], dashed=True)
    c.arrow(1220, 716, 1220, 696, color=OPT[1], dashed=True)

    # planning engine and connectors
    c.arrow(210, 782, 210, 826, color=MUTE)
    c.text(224, 808, t["compiled"], size=11, fill=MUTE, anchor="start")
    c.box(60, 826, 1280, 66, SYSTEM)
    c.text(700, 854, t["plan"], size=16, weight=700)
    c.text(700, 876, t["plan_s"], size=12, fill=MUTE)
    c.arrow(500, 892, 500, 926, color=MUTE)
    c.box(60, 926, 760, 66, SYSTEM)
    c.text(440, 954, t["conn"], size=16, weight=700)
    c.text(440, 976, t["conn_s"], size=12, fill=MUTE)
    c.arrow(820, 959, 880, 959, color=MUTE, width=2)
    c.box(880, 926, 460, 66, DATA)
    c.text(1110, 954, t["wh"], size=16, weight=700)
    c.text(1110, 976, t["wh_s"], size=12, fill=MUTE)

    # legend
    c.text(60, 1040, t["legend"], size=14, weight=700, anchor="start")
    items = [(60, CLIENT, "l_client"), (250, SYSTEM, "l_system"), (440, OPEN, "l_open"),
             (640, DATA, "l_data"), (830, OPT, "l_opt"), (1040, ROLE, "l_role")]
    for x, colors, key in items:
        c.box(x, 1054, 22, 16, colors, r=3, dashed=(key == "l_opt"), stroke_w=1.2)
        c.text(x + 30, 1067, t[key], size=12, fill=MUTE, anchor="start")
    c.arrow(60, 1100, 100, 1100, color=MUTE)
    c.text(110, 1104, t["l_flow"], size=12, fill=MUTE, anchor="start")
    c.arrow(330, 1100, 370, 1100, color=OPT[1], dashed=True)
    c.text(380, 1104, t["l_opt_flow"], size=12, fill=MUTE, anchor="start")

    return c.svg()


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for lang, name in [("en", "janus-ai-flow"), ("zh-CN", "janus-ai-flow.zh-CN")]:
        svg = build(lang)
        (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(ASSETS / f"{name}.png"),
                         output_width=W * 2)
        print("wrote", ASSETS / f"{name}.png")


if __name__ == "__main__":
    main()

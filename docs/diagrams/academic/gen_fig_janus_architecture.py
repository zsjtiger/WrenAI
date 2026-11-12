"""Generate fig_janus_architecture.svg (academic-diagram, Style A: Academic Mono).

Layout is a layered stack, top to bottom:
  agents -> access interfaces -> open context layer -> review band (draft/apply)
  -> planning engine -> connectors -> data sources.
Grayscale only; meaning is carried by line weight, dash pattern, and fill.
"""

from html import escape
from pathlib import Path

import sys

LANG = "zh" if "zh" in sys.argv[1:] else "en"
ZH = {
    "Coding agents": "编码代理", "Claude Code, Cursor": "Claude Code、Cursor",
    "Chat assistants": "聊天助手", "ChatGPT, internal copilots": "ChatGPT、内部助手",
    "MCP clients and apps": "MCP 客户端与应用", "CReport app, MCP hosts": "CReport 应用、MCP 宿主",
    "janus CLI · Python SDK": "janus CLI · Python SDK", "queries, context, memory": "查询、上下文、记忆",
    "MCP server · HTTP API": "MCP 服务 · HTTP API", "tools and endpoints": "工具与接口",
    "janus-core-wasm": "janus-core-wasm", "planning in the browser": "浏览器内规划",
    "Open context layer": "开放上下文层",
    "Ontology (MDL)": "本体（MDL）", "models · relationships": "模型 · 关系",
    "terms · inferred keys": "术语 · 推断的外键",
    "Knowledge": "知识", "rules · enums": "规则 · 枚举", "mined SQL attributes": "挖掘出的 SQL 属性",
    "Memory": "记忆", "LanceDB hybrid index": "LanceDB 混合索引", "recall of NL→SQL": "召回 NL→SQL",
    "Governed execution": "受治理的执行", "certified models": "认证模型",
    "provenance · dry-plan": "溯源 · dry-plan",
    "Review & apply": "审核与应用", "agent proposals,": "代理提议，", "human approval": "人工批准",
    "Draft (draft/)": "草稿（draft/）", "infer-fks · terms · attributes": "推断外键 · 术语 · 属性",
    "Embedding model": "嵌入模型", "frozen · optional": "冻结 · 可选", "Chat model": "聊天模型",
    "suggestions": "建议", "compiled MDL": "编译后的 MDL",
    "Planning engine: janus-core (Rust)": "规划引擎：janus-core（Rust）",
    "MDL expansion · CTE rewrite · policy checks": "MDL 展开 · CTE 改写 · 策略检查",
    "Connectors": "连接器", "20 data sources · dialect-specific SQL": "20 个数据源 · 各方言 SQL",
    "Data warehouses and databases": "数据仓库与数据库",
    "query and data flow": "查询与数据流", "query and data flow ": "查询与数据流",
    "optional model call (frozen)": "可选模型调用（冻结）", "optional model call": "可选模型调用",
    "frozen component": "冻结组件",
    "external agents and clients": "外部代理与客户端", "system components": "系统组件",
    "proposed open context layer": "本项目提出的开放上下文层",
    "data and draft artifacts": "数据与草稿工件", "optional frozen models": "可选冻结模型",
}
ZH_FONT = "'WenQuanYi Zen Hei', 'PingFang SC', 'Microsoft YaHei', sans-serif"


def T(text):
    return ZH.get(text, text) if LANG == "zh" else text


W, H = 960, 630
INK = "#1a1a1a"
MUTED = "#595959"
GRAY = "#757575"
EMPH = "#e8e8e8"

lines: list[str] = []
add = lines.append


def box(x, y, w, h, title, sub1=None, sub2=None, frozen=False, emph=False):
    fill = EMPH if emph else "#ffffff"
    sw = 1.5 if emph else 1.25
    dash = ' stroke-dasharray="3,2"' if frozen else ""
    add(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" ry="4" '
        f'fill="{fill}" stroke="{INK}" stroke-width="{sw}"{dash}/>')
    cx = x + w / 2
    subs = [s for s in (sub1, sub2) if s]
    block = 14 + 12 * len(subs)  # title line plus sub-lines
    top = y + (h - block) / 2 if h >= 60 else y + 4  # center tall boxes
    add(f'  <text x="{cx}" y="{top + 12:.1f}" text-anchor="middle" font-size="11" '
        f'font-weight="600" fill="{INK}">{escape(T(title))}</text>')
    yy = top + 26
    for s in (sub1, sub2):
        if s:
            add(f'  <text x="{cx}" y="{yy}" text-anchor="middle" font-size="9" '
                f'fill="{MUTED}">{escape(T(s))}</text>')
            yy += 12


def line(x1, y1, x2, y2, dashed=False, marker="arrow-solid"):
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    width = 1.25 if dashed else 1.5
    add(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" '
        f'stroke-width="{width}"{dash} marker-end="url(#{marker})"/>')


def polyline(points, dashed=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    add(f'  <path d="{d}" fill="none" stroke="{INK}" stroke-width="1.25"'
        f'{dash} marker-end="url(#arrow-solid)"/>')


def label(x, y, text, anchor="start", size=8):
    add(f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'fill="{MUTED}">{escape(T(text))}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'width="{W}" height="{H}">')
add(f"  <style>text {{ font-family: {ZH_FONT if LANG == 'zh' else chr(39)+'Helvetica Neue'+chr(39)+', Helvetica, Arial, sans-serif'}; }}</style>")
add("  <defs>")
add('    <marker id="arrow-solid" markerWidth="8" markerHeight="6" refX="7" '
    'refY="3" orient="auto">')
add(f'      <polygon points="0 0, 8 3, 0 6" fill="{INK}"/>')
add("    </marker>")
add("  </defs>")
add(f'  <rect width="{W}" height="{H}" fill="#ffffff"/>')

# 1. agents (row y=20)
agent_cols = [200, 480, 760]
for cx, (t, s) in zip(agent_cols, [
    ("Coding agents", "Claude Code, Cursor"),
    ("Chat assistants", "ChatGPT, internal copilots"),
    ("MCP clients and apps", "CReport app, MCP hosts"),
]):
    box(cx - 110, 20, 220, 44, t, s)

# 2. access interfaces (row y=118)
for cx, (t, s) in zip(agent_cols, [
    ("janus CLI · Python SDK", "queries, context, memory"),
    ("MCP server · HTTP API", "tools and endpoints"),
    ("janus-core-wasm", "planning in the browser"),
]):
    line(cx, 64, cx, 118)
    box(cx - 110, 118, 220, 44, t, s)

# 3. open context layer (container y=200..360)
for cx in agent_cols:
    line(cx, 162, cx, 200)
add(f'  <rect x="50" y="200" width="860" height="160" rx="4" ry="4" fill="#fafafa" '
    f'stroke="{GRAY}" stroke-width="1" stroke-dasharray="2,2"/>')
label(66, 216, T("Open context layer"), size=9)
pillars = [
    (68, "Ontology (MDL)", "models · relationships", "terms · inferred keys", False),
    (276, "Knowledge", "rules · enums", "mined SQL attributes", False),
    (484, "Memory", "LanceDB hybrid index", "recall of NL→SQL", False),
    (692, "Governed execution", "certified models", "provenance · dry-plan", True),
]
for x, t, s1, s2, emph in pillars:
    box(x, 236, 190, 100, t, s1, s2, emph=emph)

# 4. review band (row y=396..446)
box(68, 396, 170, 50, "Review & apply", "agent proposals,", "human approval")
box(276, 396, 190, 50, "Draft (draft/)", "infer-fks · terms · attributes")
box(484, 396, 190, 50, "Embedding model", "frozen · optional", frozen=True)
box(692, 396, 190, 50, "Chat model", "frozen · optional", frozen=True)
line(163, 396, 163, 336)            # review -> ontology (apply)
line(371, 396, 371, 336)            # draft -> knowledge (attributes)
line(579, 396, 579, 336, dashed=True)  # embedding -> memory (optional)
line(276, 421, 238, 421)            # draft -> review
polyline([(787, 446), (787, 470), (371, 470), (371, 446)], dashed=True)  # chat -> draft
label(371, 484, "suggestions", anchor="middle", size=8)

# 5. planning engine (row y=500)
line(153, 446, 153, 500)
label(160, 476, "compiled MDL", size=8)
box(68, 500, 490, 44, "Planning engine: janus-core (Rust)",
    "MDL expansion · CTE rewrite · policy checks")

# 6. connectors and data sources (row y=574)
line(300, 544, 300, 574)
box(68, 574, 490, 40, "Connectors", "20 data sources · dialect-specific SQL")
for dx, dy in [(12, 8), (8, 4)]:
    add(f'  <rect x="{648 + dx}" y="{574 + dy}" width="232" height="40" rx="4" '
        f'ry="4" fill="#ffffff" stroke="{INK}" stroke-width="1.25"/>')
add(f'  <rect x="648" y="574" width="232" height="40" rx="4" ry="4" '
    f'fill="#ffffff" stroke="{INK}" stroke-width="1.25"/>')
add(f'  <text x="764" y="598" text-anchor="middle" font-size="11" font-weight="600" '
    f'fill="{INK}">{T("Data warehouses and databases")}</text>')
line(558, 594, 648, 594)

# legend (bottom-right of the engine row, clear of all nodes)
add(f'  <g transform="translate(600,500)">')
add(f'    <line x1="0" y1="10" x2="26" y2="10" stroke="{INK}" stroke-width="1.5" '
    f'marker-end="url(#arrow-solid)"/>')
add(f'    <text x="34" y="13" font-size="9" fill="{MUTED}">{T("query and data flow")}</text>')
add(f'    <line x1="0" y1="30" x2="26" y2="30" stroke="{INK}" stroke-width="1.25" '
    f'stroke-dasharray="4,3" marker-end="url(#arrow-solid)"/>')
add(f'    <text x="34" y="33" font-size="9" fill="{MUTED}">{T("optional model call (frozen)")}</text>')
add(f'    <rect x="0" y="42" width="22" height="10" rx="2" ry="2" fill="#ffffff" '
    f'stroke="{INK}" stroke-width="1.25" stroke-dasharray="3,2"/>')
add(f'    <text x="34" y="51" font-size="9" fill="{MUTED}">{T("frozen component")}</text>')
add("  </g>")

add("</svg>")

out = Path(__file__).with_name("fig_janus_architecture" + ("_zh" if LANG == "zh" else "") + ".svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

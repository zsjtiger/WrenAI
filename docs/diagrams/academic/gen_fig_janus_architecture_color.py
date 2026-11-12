"""Generate fig_janus_architecture_color.svg (academic-diagram, Style B: Academic Accent).

Same layout as gen_fig_janus_architecture.py. Color carries the category, using
the Okabe-Ito colorblind-safe palette:
  sky blue   external agents and clients
  blue       system components (access, engine, connectors)
  orange     the proposed open context layer (governed execution emphasized)
  green      data and draft artifacts
  purple     optional frozen models (dashed border)
Nodes are white with a colored stroke and a 12% tint fill. Arrows stay black,
except optional model calls, which are dashed purple.
"""

from html import escape
from pathlib import Path

W, H = 960, 630
INK = "#1a1a1a"
MUTED = "#595959"
SKY = "#56B4E9"
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
PURPLE = "#CC79A7"

lines: list[str] = []
add = lines.append


def box(x, y, w, h, title, sub1=None, sub2=None, color=BLUE,
        frozen=False, emph=False):
    opacity = 0.2 if emph else 0.12
    sw = 1.75 if emph else 1.5
    dash = ' stroke-dasharray="3,2"' if frozen else ""
    add(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" ry="4" '
        f'fill="{color}" fill-opacity="{opacity}" stroke="{color}" '
        f'stroke-width="{sw}"{dash}/>')
    cx = x + w / 2
    subs = [s for s in (sub1, sub2) if s]
    block = 14 + 12 * len(subs)
    top = y + (h - block) / 2 if h >= 60 else y + 4
    add(f'  <text x="{cx}" y="{top + 12:.1f}" text-anchor="middle" font-size="11" '
        f'font-weight="600" fill="{INK}">{escape(title)}</text>')
    yy = top + 26
    for s in subs:
        add(f'  <text x="{cx}" y="{yy:.1f}" text-anchor="middle" font-size="9" '
            f'fill="{MUTED}">{escape(s)}</text>')
        yy += 12


def line(x1, y1, x2, y2, dashed=False, color=INK, marker="arrow-solid"):
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    width = 1.25 if dashed else 1.5
    add(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{width}"{dash} marker-end="url(#{marker})"/>')


def polyline(points, dashed=False, color=INK):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    add(f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="1.25"'
        f'{dash} marker-end="url(#arrow-solid)"/>')


def label(x, y, text, anchor="start", size=8):
    add(f'  <text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'fill="{MUTED}">{escape(text)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'width="{W}" height="{H}">')
add("  <style>text { font-family: 'Helvetica Neue', Helvetica, Arial, "
    "'PingFang SC', 'Microsoft YaHei', sans-serif; }</style>")
add("  <defs>")
add('    <marker id="arrow-solid" markerWidth="8" markerHeight="6" refX="7" '
    'refY="3" orient="auto">')
add(f'      <polygon points="0 0, 8 3, 0 6" fill="{INK}"/>')
add("    </marker>")
add("  </defs>")
add(f'  <rect width="{W}" height="{H}" fill="#ffffff"/>')

# 1. external agents and clients (sky blue)
agent_cols = [200, 480, 760]
for cx, (t, s) in zip(agent_cols, [
    ("Coding agents", "Claude Code, Cursor"),
    ("Chat assistants", "ChatGPT, internal copilots"),
    ("MCP clients and apps", "CReport app, MCP hosts"),
]):
    box(cx - 110, 20, 220, 44, t, s, color=SKY)

# 2. access interfaces (blue)
for cx, (t, s) in zip(agent_cols, [
    ("janus CLI · Python SDK", "queries, context, memory"),
    ("MCP server · HTTP API", "tools and endpoints"),
    ("janus-core-wasm", "planning in the browser"),
]):
    line(cx, 64, cx, 118)
    box(cx - 110, 118, 220, 44, t, s, color=BLUE)

# 3. open context layer (orange: the proposed layer)
for cx in agent_cols:
    line(cx, 162, cx, 200)
add(f'  <rect x="50" y="200" width="860" height="160" rx="4" ry="4" fill="none" '
    f'stroke="{ORANGE}" stroke-width="1.25" stroke-dasharray="2,2"/>')
label(66, 216, "Open context layer", size=9)
pillars = [
    (68, "Ontology (MDL)", "models · relationships", "terms · inferred keys", False),
    (276, "Knowledge", "rules · enums", "mined SQL attributes", False),
    (484, "Memory", "LanceDB hybrid index", "recall of NL→SQL", False),
    (692, "Governed execution", "certified models", "provenance · dry-plan", True),
]
for x, t, s1, s2, emph in pillars:
    box(x, 236, 190, 100, t, s1, s2, color=ORANGE, emph=emph)

# 4. draft and review band (green: artifacts) and optional frozen models (purple)
box(68, 396, 170, 50, "Review & apply", "agent proposals,", "human approval", color=GREEN)
box(276, 396, 190, 50, "Draft (draft/)", "infer-fks · terms · attributes", color=GREEN)
box(484, 396, 190, 50, "Embedding model", "frozen · optional", color=PURPLE, frozen=True)
box(692, 396, 190, 50, "Chat model", "frozen · optional", color=PURPLE, frozen=True)
line(163, 396, 163, 336)
line(371, 396, 371, 336)
line(579, 396, 579, 336, dashed=True, color=PURPLE)
line(276, 421, 238, 421)
polyline([(787, 446), (787, 470), (371, 470), (371, 446)], dashed=True, color=PURPLE)
label(371, 484, "suggestions", anchor="middle", size=8)

# 5. planning engine (blue)
line(153, 446, 153, 500)
label(160, 476, "compiled MDL", size=8)
box(68, 500, 490, 44, "Planning engine: janus-core (Rust)",
    "MDL expansion · CTE rewrite · policy checks", color=BLUE)

# 6. connectors (blue) and data sources (green)
line(300, 544, 300, 574)
box(68, 574, 490, 40, "Connectors", "20 data sources · dialect-specific SQL", color=BLUE)
for dx, dy in [(12, 8), (8, 4)]:
    add(f'  <rect x="{648 + dx}" y="{574 + dy}" width="232" height="40" rx="4" '
        f'ry="4" fill="{GREEN}" fill-opacity="0.12" stroke="{GREEN}" stroke-width="1.5"/>')
add(f'  <rect x="648" y="574" width="232" height="40" rx="4" ry="4" '
    f'fill="{GREEN}" fill-opacity="0.12" stroke="{GREEN}" stroke-width="1.5"/>')
add(f'  <text x="764" y="598" text-anchor="middle" font-size="11" font-weight="600" '
    f'fill="{INK}">Data warehouses and databases</text>')
line(558, 594, 648, 594)

# legend: categories (left column) and line types (right column), clear of nodes
add('  <g transform="translate(600,488)">')
legend = [(SKY, "external agents and clients"),
          (BLUE, "system components"),
          (ORANGE, "proposed open context layer"),
          (GREEN, "data and draft artifacts"),
          (PURPLE, "optional frozen models")]
for i, (c, text) in enumerate(legend):
    y = i * 15
    add(f'    <rect x="0" y="{y}" width="14" height="10" rx="2" ry="2" '
        f'fill="{c}" fill-opacity="0.2" stroke="{c}" stroke-width="1.25"/>')
    add(f'    <text x="20" y="{y + 9}" font-size="9" fill="{MUTED}">{escape(text)}</text>')
add("  </g>")
add('  <g transform="translate(770,488)">')
add(f'    <line x1="0" y1="8" x2="24" y2="8" stroke="{INK}" stroke-width="1.5" '
    f'marker-end="url(#arrow-solid)"/>')
add(f'    <text x="30" y="11" font-size="9" fill="{MUTED}">query and data flow</text>')
add(f'    <line x1="0" y1="30" x2="24" y2="30" stroke="{PURPLE}" stroke-width="1.25" '
    f'stroke-dasharray="4,3" marker-end="url(#arrow-solid)"/>')
add(f'    <text x="30" y="33" font-size="9" fill="{MUTED}">optional model call</text>')
add("  </g>")

add("</svg>")

out = Path(__file__).with_name("fig_janus_architecture_color.svg")
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out)

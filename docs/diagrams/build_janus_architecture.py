import html, pathlib
from xml.sax.saxutils import quoteattr

OUT = pathlib.Path("/home/user/WrenAI/docs/diagrams/janus-ai-architecture.drawio")
INK, MUTE, LINE, PANEL, PANELB = "#0f172a", "#8a93a3", "#c9d0dc", "#fbfcfe", "#d7dce6"
PILL, PILLB, ACC, PURP, CYAN, WHITE = "#eef1f6", "#cfd6e2", "#2f5bea", "#7b5cf0", "#14b8c8", "#ffffff"
SANS, MONO = "Inter", "DejaVu Sans Mono"

cells, nid = [], [2]
def new_id():
    nid[0] += 1
    return str(nid[0])

def add(style, x, y, w, h, value="", vertex=True):
    i = new_id()
    cells.append(
        f'<mxCell id="{i}" value={quoteattr(value)} style={quoteattr(style)} vertex="{1 if vertex else 0}" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return i

def text(x, y, w, value, size=14, color=INK, font=SANS, align="left", h=None, bold=False):
    h = h or round(size * 1.5)
    style = (f"text;html=0;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;"
             f"whiteSpace=nowrap;fontSize={size};fontColor={color};fontFamily={font};"
             + ("fontStyle=1;" if bold else ""))
    return add(style, x, y, w, h, value)

def mono_text(x, y, w, value, size=12, color=MUTE, align="left"):
    return text(x, y, w, value, size=size, color=color, font=MONO, align=align)

def rect(x, y, w, h, fill, stroke, rounded=True, r=14, extra=""):
    style = (f"rounded={1 if rounded else 0};arcSize={r * 100 // max(w, h, 1)};fillColor={fill};"
             f"strokeColor={stroke};strokeWidth=1;" + extra)
    return add(style, x, y, w, h, "")

def dot(cx, cy, fill, stroke, r=4.5):
    return add(f"shape=ellipse;perimeter=ellipsePerimeter;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;", cx - r, cy - r, 2 * r, 2 * r, "")

def curve(x1, y1, x2, y2, color, width=1.2, arrow=False):
    i = new_id()
    end = "block" if arrow else "none"
    style = (f"edgeStyle=none;curved=1;endArrow={end};endSize=5;html=0;strokeColor={color};"
             f"strokeWidth={width};")
    dy = y2 - y1
    pts = (f'<Array as="points"><mxPoint x="{x1}" y="{y1 + dy * 0.45:.1f}"/>'
           f'<mxPoint x="{x2}" y="{y1 + dy * 0.55:.1f}"/></Array>')
    cells.append(
        f'<mxCell id="{i}" value="" style={quoteattr(style)} edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/>'
        f'{pts}</mxGeometry></mxCell>')

# ---- canvas ----
add("rounded=0;fillColor=#f5f7fb;strokeColor=none;", 0, 0, 1280, 1000, "")

# header
mono_text(100, 26, 600, "A · BRING THE AGENTS YOU ALREADY RUN")
mono_text(780, 26, 400, "FIG. 02 · SYSTEM ARCHITECTURE", align="right")
add(f"rounded=0;fillColor={LINE};strokeColor=none;", 100, 52, 1080, 1, "")

# top agents
add(f"rounded=0;fillColor=#f5f7fb;strokeColor=none;", 470, 196, 340, 44, "")
agent_x = [186, 366, 549, 731, 913, 1096]
agents = ["Claude Code", "Cursor", "ChatGPT", "Internal copilots", "MCP clients", "JanusAI CReport app"]
end_x = [301, 438, 573, 707, 842, 977]
for k, (x, name) in enumerate(zip(agent_x, agents)):
    text(x - 110, 110, 220, name, size=21, align="center")
    dot(x, 176, WHITE, MUTE, 4.5)
    curve(x, 176, end_x[k], 280, PURP if k == 0 else LINE, 2.2 if k == 0 else 1.2, arrow=True)

mono_text(440, 200, 400, "QUERIES ↓", size=13, color=MUTE, align="center")
mono_text(440, 222, 400, "NL · SQL · MCP TOOLS", size=12, color=MUTE, align="center")

# central panel
rect(112, 280, 1056, 384, PANEL, PANELB, r=14)
add(f"rounded=0;fillColor={PURP};gradientColor={CYAN};gradientDirection=east;strokeColor=none;", 112, 279, 1056, 2, "")
text(198, 290, 700, "Open Context Layer", size=36)
text(198, 344, 800, "Governed CReport for any agent, from context you can read, diff, and own.", size=16, color=MUTE)
for k, line in enumerate(["B · FREE FOREVER", "RUNS WITHOUT US", "YOUR CONTEXT STAYS IN YOUR GIT"]):
    mono_text(842, 306 + k * 22, 300, line, size=13, align="right")
add(f"rounded=0;fillColor={PANELB};strokeColor=none;", 136, 387, 1008, 1, "")

cols = [147, 400, 652, 904]
pillars = [
    ("01", "MDL", "WHAT YOUR DATA MEANS", ["models · relationships", "views · cubes & metrics"]),
    ("02", "Knowledge", "WHAT SCHEMAS DON'T SAY", ["instructions.md · enums", "queries.yml · approved joins"]),
    ("03", "Memory", "WHAT WORKED BEFORE", ["LanceDB hybrid index", "recall of proven NL→SQL"]),
    ("04", "Governed execution", "WHAT AGENTS MAY RUN", ["dry-plan · row limits", "structured errors, hints"]),
]
for k, (num, title, sub, body) in enumerate(pillars):
    x = cols[k]
    mono_text(x, 402, 60, num, size=13)
    text(x + 84, 432, 240, title, size=22)
    mono_text(x + 84, 468, 240, sub, size=11)
    mono_text(x, 500, 240, body[0], size=13, color=INK)
    mono_text(x, 520, 240, body[1], size=13, color=INK)
    if k:
        add(f"rounded=0;fillColor={LINE};strokeColor=none;", x - 14, 402, 1, 146, "")

# icons (simple shapes; style checked against the reference)
x = cols[0]
add(f"shape=triangle;direction=north;perimeter=trianglePerimeter;fillColor=none;strokeColor={INK};strokeWidth=2;", x + 2, 452, 48, 40, "")
for cx, cy in [(x + 26, 452), (x + 2, 492), (x + 50, 492)]:
    dot(cx, cy, WHITE, INK, 4)
dot(x + 26, 474, ACC, ACC, 2.5)
x = cols[1]
add(f"rounded=0;fillColor=none;strokeColor={INK};strokeWidth=2;", x, 446, 42, 52, "")
add(f"rounded=0;fillColor={ACC};strokeColor=none;", x, 446, 42, 9, "")
for ly in (470, 480, 490):
    add(f"rounded=0;fillColor={INK};strokeColor=none;", x + 8, ly, 26, 2, "")
x = cols[2]
add(f"shape=ellipse;perimeter=ellipsePerimeter;fillColor=none;strokeColor={INK};strokeWidth=1.6;", x - 2, 448, 56, 56, "")
add(f"shape=ellipse;perimeter=ellipsePerimeter;fillColor=none;strokeColor={INK};strokeWidth=2;", x + 14, 472, 16, 16, "")
dot(x + 26, 480, INK, INK, 2.5)
x = cols[3]
add(f"shape=ellipse;perimeter=ellipsePerimeter;fillColor=none;strokeColor={INK};strokeWidth=2;", x + 4, 452, 52, 52, "")
add(f"rounded=0;fillColor={PANEL};strokeColor=none;", x - 4, 478, 66, 18, "")
add(f"endArrow=none;html=0;strokeColor={CYAN};strokeWidth=2.5;", x + 2, 498, 0, 0, "", vertex=False) if False else None
curve(x + 29, 492, x + 46, 468, CYAN, 2.5)
dot(x + 29, 492, CYAN, CYAN, 4)

# access modes
add(f"rounded=0;fillColor={LINE};strokeColor=none;", 136, 574, 1008, 1, "")
add(f"rounded=0;fillColor={PANEL};strokeColor=none;", 460, 566, 360, 18, "")
mono_text(460, 566, 360, "ACCESS MODES · ONE ENGINE, EVERY SURFACE", size=12, align="center")
pills = [(211, 308, "janus CLI"), (320, 435, "Python SDK"), (446, 561, "MCP server"),
         (572, 831, "janus-core-wasm · in-browser"), (843, 1068, "LangChain · Pydantic AI")]
for x0, x1, label in pills:
    add(f"rounded=1;arcSize=50;fillColor={PILL};strokeColor={PILLB};", x0, 596, x1 - x0, 34, "")
    mono_text(x0, 596, x1 - x0, label, size=14, color=INK, align="center")

# bottom: execution labels, sources, axis
add(f"rounded=0;fillColor=#f5f7fb;strokeColor=none;", 330, 712, 620, 44, "")
mono_text(440, 718, 400, "EXECUTES AS DIALECT-SPECIFIC SQL ↓", size=12, align="center")
mono_text(340, 738, 600, "PUSHED DOWN TO YOUR WAREHOUSE · NOTHING TO MIGRATE", size=12, align="center")
srcs = ["PostgreSQL", "BigQuery", "Snowflake", "DuckDB", "ClickHouse", "Trino",
        "Databricks", "Redshift", "Spark", "S3", "MySQL", "Athena"]
dot_x = [100, 198, 296, 394, 492, 590, 689, 787, 885, 983, 1082, 1180]
src_top = [251, 321, 392, 462, 533, 603, 675, 746, 817, 887, 958, 1029]
for k, (sx, dx, name) in enumerate(zip(src_top, dot_x, srcs)):
    hl = (dx == 394)
    curve(sx, 664, dx, 826, ACC if hl else LINE, 2.2 if hl else 1.2)
    dot(dx, 826, WHITE, MUTE, 4.5)
    text(dx - 70, 840, 140, name, size=17, align="center")

mono_text(100, 880, 600, "C · YOUR DATA, WHERE IT ALREADY LIVES", size=12)
mono_text(780, 880, 400, "12 OF 22+ SOURCES SHOWN", size=12, align="right")
add(f"rounded=0;fillColor={LINE};strokeColor=none;", 100, 906, 1080, 1, "")
mono_text(100, 920, 200, "0 SOURCES", size=12)
mono_text(540, 920, 200, "11", size=12, align="center")
mono_text(980, 920, 200, "22+ CONNECTORS", size=12, align="right")
mono_text(680, 956, 500, "COME BUILD CREPORT WITH US  ·  ★ STAR THE REPO", size=12, align="right")

xml = ('<mxfile host="Claude" modified="2026-10-13" agent="drawio-reconstruction" version="24.0.0">'
       '<diagram name="JanusAI architecture" id="arch">'
       '<mxGraphModel dx="1280" dy="1000" grid="0" gridSize="10" guides="0" tooltips="0" connect="0" '
       'arrows="1" fold="0" page="0" pageScale="1" pageWidth="1280" pageHeight="1000" math="0" shadow="0">'
       '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
       + "".join(cells) +
       '</root></mxGraphModel></diagram></mxfile>')
OUT.write_text(xml, encoding="utf-8")
print("wrote", OUT, len(cells), "cells")

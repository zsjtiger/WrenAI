# Audit: janus-ai-architecture (English)

Reference: `assets/janus-ai-architecture.png` (2560×2000, rendered at 2× from a 1280×1000 layout).
Output: `janus-ai-architecture.drawio` (native mxGraph cells), `janus-ai-architecture.png` (preview).

## Method
- Medium: native Draw.io cells for all text, panels, dividers, pills, and connectors (curved edges with two waypoints).
- Icons (triangle, document, ring, gauge): native shapes checked against the reference's outline style, not replaced with generic icons.
- Preview: rendered with the `mxgraph` engine in Chromium, because the Draw.io desktop CLI is not installed here and the viewer CDN is unreachable. The Draw.io desktop export may differ slightly in font metrics.
- Checks: `check_drawio.py` passes (132 cells, 111 vertices, 19 edges, 61 text cells).

## Inventory status
| id | element | status |
|---|---|---|
| header | "A · …" / "FIG. 02 · …" + rule | done |
| agents | six labels, dots, curves to panel | done (curves approximate the reference S-curves) |
| query label | "QUERIES ↓ / NL · SQL · MCP TOOLS" | done |
| panel | rounded panel, gradient top rule | done (no drop shadow) |
| title + subtitle + right block | "Open Context Layer", tagline, three right-aligned lines | done |
| pillars 01–04 | numbers, titles, captions, two body lines, dividers | done |
| icon 01 MDL | triangle with three vertex nodes | done |
| icon 02 Knowledge | document with blue top bar | done |
| icon 03 Memory | ring with centre dot | needs-fix: reference has a blue accent arc on the ring; not drawn |
| icon 04 Governed execution | gauge with cyan needle | needs-fix: gauge is a full outline with a panel-coloured cover, not an exact half arc |
| access modes | divider, label, five pills | done |
| execution labels | two lines over the connectors | done (connectors pass behind the text, as in the reference) |
| source curves + dots | twelve sources, DuckDB highlight | done |
| axis + scale | "C · …", rule, "0 / 11 / 22+" | done |
| footer | "COME BUILD … STAR THE REPO" | done (Apache and repository URL removed) |
| background | light page colour | needs-fix: reference has a dot grid; not drawn |

## Remaining review points
- Memory icon accent arc and gauge half-arc are approximations.
- Dot-grid background is missing.
- No dark variant was produced from this file.

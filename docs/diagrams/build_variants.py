"""Derive the README architecture variants from janus-ai-architecture.drawio.

Outputs (each a .drawio file, rendered to PNG separately):
  janus-ai-architecture.zh-CN.drawio         Chinese labels, light
  janus-ai-architecture-dark.drawio          English labels, dark
  janus-ai-architecture-dark.zh-CN.drawio    Chinese labels, dark

The layout is the same in all four. Only text and colors change. Neutral
colors are inverted for dark; saturated accents are kept.
"""

from __future__ import annotations

import html
import pathlib
import re
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "janus-ai-architecture.drawio"

ZH = {
    "A · BRING THE AGENTS YOU ALREADY RUN": "A · 让你已有的智能体直接接入",
    "FIG. 02 · SYSTEM ARCHITECTURE": "图 02 · 系统架构",
    "Internal copilots": "内部助手",
    "JanusAI CReport app": "JanusAI CReport 应用",
    "QUERIES ↓": "查询 ↓",
    "NL · SQL · MCP TOOLS": "自然语言 · SQL · MCP 工具",
    "Open Context Layer": "开放上下文层",
    "Governed CReport for any agent, from context you can read, diff, and own.": "面向任何智能体的受治理 CReport：上下文可读、可比对、可掌控。",
    "B · FREE FOREVER": "B · 永久免费",
    "RUNS WITHOUT US": "无需我们也能运行",
    "YOUR CONTEXT STAYS IN YOUR GIT": "上下文留在你的 Git 中",
    "WHAT YOUR DATA MEANS": "数据的业务含义",
    "models · relationships": "模型 · 关系",
    "terms · inferred keys": "术语 · 推断的外键",
    "Knowledge": "知识",
    "WHAT SCHEMAS DON'T SAY": "Schema 没有说明的内容",
    "knowledge/rules · enums": "knowledge/rules · 枚举",
    "mined SQL attributes": "挖掘出的 SQL 属性",
    "Memory": "记忆",
    "WHAT WORKED BEFORE": "过去有效的做法",
    "LanceDB hybrid index": "LanceDB 混合索引",
    "recall of proven NL→SQL": "召回已验证的 NL→SQL",
    "Governed execution": "受治理的执行",
    "WHAT AGENTS MAY RUN": "智能体可以运行的内容",
    "certified models · provenance": "认证模型 · 溯源",
    "dry-plan · row limits": "dry-plan · 行数上限",
    "ACCESS MODES · ONE ENGINE, EVERY SURFACE": "访问方式 · 一个引擎，所有入口",
    "janus-core-wasm · in-browser": "janus-core-wasm · 浏览器内",
    "EXECUTES AS DIALECT-SPECIFIC SQL ↓": "按各方言执行 SQL ↓",
    "PUSHED DOWN TO YOUR WAREHOUSE · NOTHING TO MIGRATE": "下推到你的数据仓库 · 无需迁移",
    "C · YOUR DATA, WHERE IT ALREADY LIVES": "C · 数据留在原处",
    "12 OF 20 SOURCES SHOWN": "展示 12 / 20 个数据源",
    "0 SOURCES": "0 个数据源",
    "20 CONNECTORS": "20 个连接器",
    "COME BUILD CREPORT WITH US  ·  ★ STAR THE REPO": "欢迎一起构建 CReport  ·  ★ 给仓库点星",
}

_HEX = re.compile(r"#([0-9a-fA-F]{6})\b")


def _translate(xml: str) -> str:
    def swap(match: re.Match) -> str:
        original = html.unescape(match.group(2))
        if original in ZH:
            return match.group(1) + escape(ZH[original], {'"': "&quot;"}) + match.group(3)
        return match.group(0)

    out = re.sub(r'(<mxCell id="\d+" value=")([^"]*)(")', swap, xml)
    return out.replace("fontFamily=Inter", "fontFamily=WenQuanYi Zen Hei")


def _darken_neutrals(xml: str) -> str:
    """Invert neutral (low-saturation) colors; keep saturated accents."""

    def invert(match: re.Match) -> str:
        r, g, b = (int(match.group(1)[i:i + 2], 16) for i in (0, 2, 4))
        if max(r, g, b) - min(r, g, b) >= 40:
            return match.group(0)
        return "#{:02x}{:02x}{:02x}".format(255 - r, 255 - g, 255 - b)

    return _HEX.sub(invert, xml)


def main() -> None:
    light = SOURCE.read_text(encoding="utf-8")
    outputs = {
        "janus-ai-architecture.zh-CN.drawio": _translate(light),
        "janus-ai-architecture-dark.drawio": _darken_neutrals(light),
        "janus-ai-architecture-dark.zh-CN.drawio": _darken_neutrals(_translate(light)),
    }
    for name, content in outputs.items():
        (HERE / name).write_text(content, encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()

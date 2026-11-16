"""Call the janus MCP server the way an agent does: list tools, run SQL.

The server is started over stdio, as `janus serve mcp --project <dir>`.

    JANUS_HOME=... python mcp_client.py <project_dir>

Environment:
    JANUS           command that starts janus (default: janus)
    JANUS_HOME      where profiles.yml lives (set by run_demo.sh)
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

QUERIES = [
    "SELECT customer_id, name, region FROM customers ORDER BY customer_id",
    (
        "SELECT o.order_id, c.name, o.amount, o.status "
        "FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
        "WHERE o.status = 'shipped' ORDER BY o.order_id"
    ),
]


async def main(project: Path) -> None:
    janus = shlex.split(os.environ.get("JANUS", "janus"))
    params = StdioServerParameters(
        command=janus[0],
        args=[*janus[1:], "serve", "mcp", "--project", str(project), "--quiet"],
        env={**os.environ},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("tools:", ", ".join(names))
            print()

            for sql in QUERIES:
                print(f"> {sql}")
                result = await session.call_tool("run_sql", {"sql": sql})
                payload = json.loads(result.content[0].text)
                for row in payload.get("rows", []):
                    print("   ", row)
                prov = payload.get("provenance", {})
                print(f"    models used: {prov.get('models')}")
                print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: mcp_client.py <project_dir>")
    asyncio.run(main(Path(sys.argv[1]).resolve()))

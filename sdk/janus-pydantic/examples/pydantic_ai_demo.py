"""3-line quickstart: attach a CLI-prepared Janus project to a Pydantic AI agent.

Prereq:
    janus profile add my_project --datasource duckdb
    janus context init
    janus context set-profile my_project
    janus context build

Run:
    OPENAI_API_KEY=sk-... python examples/pydantic_ai_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic_ai import Agent

from janus_pydantic import JanusToolkit


def main() -> None:
    project_path = Path(os.environ.get("PROJECT_PATH", "./analytics_db")).expanduser()
    if not (project_path / "janus_project.yml").exists():
        print(
            f"PROJECT_PATH={project_path} doesn't look like a Janus project "
            "(no janus_project.yml). Run `janus context init` there first, "
            "or set PROJECT_PATH to an existing project.",
            file=sys.stderr,
        )
        sys.exit(1)

    toolkit = JanusToolkit.from_project(project_path)
    agent = Agent(
        "openai:gpt-4o",
        instructions=toolkit.instructions(),
        toolsets=[toolkit.toolset()],
    )

    question = "How many rows are in each model in this project?"
    result = agent.run_sync(question)
    print(f"Q: {question}\n")
    print(result.output)


if __name__ == "__main__":
    main()

"""Helpers shared by the ``janus`` CLI sub-apps."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

ProjectPathOpt = Annotated[
    Optional[str],
    typer.Option(
        "--path",
        "-p",
        help="Project directory. Auto-detected via JANUS_PROJECT_HOME, cwd walk, or ~/.janus/config.yml.",
    ),
]


def resolve_project_path(path: str | None = None):
    """Return the project directory, or exit with the discovery error on stderr."""
    from janus.context import discover_project_path  # noqa: PLC0415

    try:
        return discover_project_path(path)
    except SystemExit as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

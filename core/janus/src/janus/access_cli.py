"""``janus access`` commands: check a role-based access config against the project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from janus.cli_common import ProjectPathOpt, resolve_project_path

access_app = typer.Typer(
    name="access",
    help="Role-based row and column access: check and report.",
    no_args_is_help=True,
)


@access_app.command("report")
def report(
    path: ProjectPathOpt = None,
    access_config: Annotated[
        Optional[str],
        typer.Option(
            "--access-config",
            envvar="JANUS_ACCESS_CONFIG",
            help="The access config (janus_access.yml) to check. Required.",
        ),
    ] = None,
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", help="Connection profile the roles' SQL runs on."),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Machine-readable output.")
    ] = False,
) -> None:
    """Evaluate each role, cross-check it with the model, and print what it can see.

    Exit code: 0 when the config is consistent, 1 when there are errors (startup
    would be refused), 2 when the config or project cannot be read.
    """
    from janus.access import (  # noqa: PLC0415
        AccessConfigError,
        build_runtime,
        format_report,
        load_access_config,
        table_rows,
    )
    from janus.cli import _build_engine  # noqa: PLC0415
    from janus.serve_cli import _profile_connection_info  # noqa: PLC0415

    if not access_config:
        typer.echo("Error: pass --access-config <janus_access.yml>", err=True)
        raise typer.Exit(2)
    project_path = resolve_project_path(path)
    mdl_path = project_path / "target" / "mdl.json"
    if not mdl_path.exists():
        typer.echo(
            "Error: no target/mdl.json. Run `janus context build` first.", err=True
        )
        raise typer.Exit(2)
    try:
        config = load_access_config(Path(access_config))
    except AccessConfigError as exc:
        typer.echo(f"Error: access config: {exc}", err=True)
        raise typer.Exit(2) from exc

    connection_info = _profile_connection_info(profile) if profile is not None else None
    engine = _build_engine(str(mdl_path), connection_info, None, conn_required=True)
    try:
        mdl = json.loads(mdl_path.read_text(encoding="utf-8"))
        runtime = build_runtime(
            config,
            mdl,
            lambda sql: table_rows(engine.query_with_provenance(sql, 10, None)[0]),
        )
    except AccessConfigError as exc:
        if as_json:
            typer.echo(json.dumps({"errors": str(exc).split("; ")}, indent=2))
        else:
            typer.echo(f"error: {exc}")
        raise typer.Exit(1) from exc
    finally:
        if hasattr(engine, "close"):
            engine.close()

    if as_json:
        typer.echo(
            json.dumps(
                {
                    "errors": [],
                    "warnings": runtime.check.warnings,
                    "report": runtime.check.report,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        typer.echo(format_report(runtime.check))
        if not runtime.check.warnings:
            typer.echo("ok: no errors or warnings")

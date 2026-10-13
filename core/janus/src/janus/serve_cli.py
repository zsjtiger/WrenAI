"""Typer sub-app for ``janus serve`` commands."""

from __future__ import annotations

import atexit
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from janus.cli_common import resolve_project_path

serve_app = typer.Typer(
    name="serve",
    help="Serve janus capabilities to external clients (MCP, ...).",
)

_SOURCE_FILES = ("janus_project.yml", "relationships.yml")
_SOURCE_DIRS = ("models", "views", "cubes")


def _mdl_is_stale(project: Path, mdl_path: Path) -> bool:
    """Return True if any project source file is newer than mdl_path."""
    mdl_mtime = mdl_path.stat().st_mtime

    for name in _SOURCE_FILES:
        f = project / name
        if f.exists() and f.stat().st_mtime > mdl_mtime:
            return True

    for dirname in _SOURCE_DIRS:
        d = project / dirname
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.stat().st_mtime > mdl_mtime:
                return True

    return False


def _serve_args(
    project: Path, profile: str | None, allow_write: bool, no_connect: bool
) -> list[str]:
    """Reconstruct the stdio `serve mcp` args for a client config."""
    args = ["serve", "mcp", "--project", str(project)]
    if profile:
        args += ["--profile", profile]
    if allow_write:
        args.append("--allow-write")
    if no_connect:
        args.append("--no-connect")
    return args


def _print_connection_help(
    *,
    transport: str,
    host: str,
    port: int,
    project: Path,
    profile: str | None,
    allow_write: bool,
    no_connect: bool,
) -> None:
    """Print client-registration guidance.

    Always to stderr — on stdio transport, stdout is the MCP protocol channel
    and must not be polluted.
    """
    janus_cmd = shutil.which("janus") or sys.argv[0] or "janus"
    janus_home = os.environ.get("JANUS_HOME")
    line = "─" * 68

    def echo(msg: str = "") -> None:
        typer.echo(msg, err=True)

    echo(line)
    if transport == "http":
        # A wildcard bind host isn't a connectable client target — show loopback.
        display_host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
        url = f"http://{display_host}:{port}/mcp"
        echo(" janus MCP server — Streamable HTTP")
        echo(f"   URL: {url}")
        echo("")
        echo(" Register with a client:")
        echo(f"   Claude Code   claude mcp add --transport http janus {url}")
        echo(f"   Codex         codex mcp add janus --url {url}")
        echo(
            "   Inspector     npx @modelcontextprotocol/inspector   "
            "(Streamable HTTP → the URL above)"
        )
        echo("")
        echo(" Press Ctrl+C to stop.")
    else:
        args = _serve_args(project, profile, allow_write, no_connect)
        # Shell-quote every token so paths with spaces stay copy-pasteable.
        cmd = " ".join(shlex.quote(t) for t in [janus_cmd, *args])
        env_flag = (
            f" -e {shlex.quote('JANUS_HOME=' + janus_home)}" if janus_home else ""
        )
        echo(" janus MCP server — stdio (your MCP client spawns this process)")
        echo("")
        echo(" Register with a client:")
        echo(f"   Claude Code   claude mcp add janus{env_flag} -- {cmd}")
        echo(f"   Codex         codex mcp add janus{env_flag} -- {cmd}")
        echo("")
        echo(" Or add to an IDE MCP config (Claude Desktop / Cursor / VS Code):")
        server: dict = {"command": janus_cmd, "args": args}
        if janus_home:
            server["env"] = {"JANUS_HOME": janus_home}
        config = {"mcpServers": {"janus": server}}
        for cfg_line in json.dumps(config, indent=2).splitlines():
            echo(f"   {cfg_line}")
        echo("")
        echo(" Waiting for a client on stdin…")
    echo(line)


@serve_app.command("mcp")
def serve_mcp(
    transport: Annotated[
        str,
        typer.Option("--transport", help="Transport: stdio or http."),
    ] = "stdio",
    host: Annotated[
        str, typer.Option("--host", help="Bind host for --transport http.")
    ] = "127.0.0.1",
    port: Annotated[
        int, typer.Option("--port", help="Bind port for --transport http.")
    ] = 8080,
    project: Annotated[
        Optional[Path],
        typer.Option("--project", help="Override project root."),
    ] = None,
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", help="Connection profile name."),
    ] = None,
    allow_write: Annotated[
        bool,
        typer.Option("--allow-write", help="Enable the store_query write tool."),
    ] = False,
    no_connect: Annotated[
        bool,
        typer.Option(
            "--no-connect",
            help="Transpile-only mode: disable run_sql, dry_run, and query_cube.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress the client-registration help banner.",
        ),
    ] = False,
) -> None:
    """Serve janus's query + context/knowledge tools as an MCP server.

    Backed by an in-process JanusEngine — no ibis-server, no HTTP engine.
    """
    _check_transport(transport)
    _ensure_mcp_installed()

    from loguru import logger  # noqa: PLC0415

    from janus.cli import _build_engine  # noqa: PLC0415

    project_path = resolve_project_path(str(project) if project else None)
    mdl_path = _require_mdl_file(project_path)

    if _mdl_is_stale(project_path, mdl_path):
        logger.warning(
            "MDL may be stale — re-run `janus context build`",
        )

    connection_info = _profile_connection_info(profile) if profile is not None else None

    engine = _build_engine(
        str(mdl_path), connection_info, None, conn_required=not no_connect
    )
    atexit.register(lambda: engine.close() if hasattr(engine, "close") else None)

    from janus.mcp_server import ServeContext, run_server  # noqa: PLC0415

    ctx = ServeContext(
        project=project_path,
        engine=engine,
        allow_write=allow_write,
        no_connect=no_connect,
    )
    if not quiet:
        _print_connection_help(
            transport=transport,
            host=host,
            port=port,
            project=project_path,
            profile=profile,
            allow_write=allow_write,
            no_connect=no_connect,
        )
    run_server(ctx, transport=transport, host=host, port=port)


def _check_transport(transport: str) -> None:
    if transport not in {"stdio", "http"}:
        typer.echo(
            f"Error: unsupported --transport '{transport}'. Use stdio or http.",
            err=True,
        )
        raise typer.Exit(1)


def _ensure_mcp_installed() -> None:
    try:
        import mcp  # noqa: F401, PLC0415
    except ImportError:
        typer.echo(
            "Install the MCP extra: pip install 'janusai[mcp]'",
            err=True,
        )
        raise typer.Exit(1)


def _require_mdl_file(project_path: Path) -> Path:
    """Resolve the MDL from the already-discovered project root.

    Not via cli._require_mdl(None): that re-discovers the project from cwd and
    would silently ignore --project.
    """
    mdl_path = project_path / "target" / "mdl.json"
    if not mdl_path.exists():
        typer.echo(
            f"Error: project found at {project_path} but target/mdl.json missing.\n"
            "  Hint: run `janus context build` first.",
            err=True,
        )
        raise typer.Exit(1)
    return mdl_path


def _profile_connection_info(profile: str) -> str:
    """Build the connection JSON for a named profile, with secrets expanded."""
    import json  # noqa: PLC0415

    from janus.profile import (  # noqa: PLC0415
        MissingSecretError,
        expand_profile_secrets,
        list_profiles,
    )

    profiles = list_profiles()
    if profile not in profiles:
        typer.echo(f"Error: profile '{profile}' not found.", err=True)
        raise typer.Exit(1)
    prof_dict = dict(profiles[profile])
    ds = prof_dict.pop("datasource", None)
    if ds is None:
        typer.echo(f"Error: profile '{profile}' has no datasource.", err=True)
        raise typer.Exit(1)
    try:
        prof_dict = expand_profile_secrets(prof_dict)
    except MissingSecretError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    return json.dumps({"datasource": ds, **prof_dict})

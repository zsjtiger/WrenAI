"""Temporary local web server for browser-based profile creation.

Usage:
    from janus.profile_web import create_app, start

    # For testing:
    app, result, server_ref = create_app("my-profile")

    # For CLI:
    result = start("my-profile", activate=True)
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from html import escape
from pathlib import Path
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from janus.model.field_registry import (
    get_fields,
    get_selectable_datasources,
    get_variants,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


_INTERNAL_FORM_KEYS = frozenset({"datasource", "_profile_name", "_variant", "_json"})


def _error_html(message: str, status_code: int = 400) -> HTMLResponse:
    return HTMLResponse(
        f'<small style="color:var(--pico-color-red-500)">{message}</small>',
        status_code=status_code,
    )


def _form_text(form, key: str) -> str | None:
    """The stripped value of a text form field, or None when absent or blank."""
    raw = form.get(key)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


async def _fields_endpoint(request: Request):
    ds = request.query_params.get("datasource", "").lower()
    variant = request.query_params.get("_variant") or None
    if not ds:
        return HTMLResponse("")
    variants = get_variants(ds)
    try:
        field_list = get_fields(ds, variant=variant)
    except ValueError:
        field_list = []
    return templates.TemplateResponse(
        request,
        "_profile_fields.html",
        {
            "datasource": ds,
            "fields": field_list,
            "variants": variants,
            "current_variant": variant or (variants[0] if variants else None),
        },
    )


def _datasource_error(ds: str, variant_key: str | None) -> HTMLResponse | None:
    """Reject an unknown datasource or a variant the datasource does not have."""
    try:
        valid_variants = get_variants(ds)
        if valid_variants and variant_key and variant_key not in valid_variants:
            return _error_html("✗ Invalid variant.")
        get_fields(ds, variant=variant_key)
    except ValueError:
        return _error_html("✗ Unsupported data source.")
    return None


def _profile_from_form(form, ds: str, variant_key: str | None) -> dict[str, Any]:
    """Build the profile dict from the form.

    ``_json`` replaces the individual fields when present; it must decode to
    an object, otherwise ``json.JSONDecodeError`` is raised for the caller.
    """
    profile: dict[str, Any] = {"datasource": ds}
    if variant_key:
        profile[f"{ds}_type"] = variant_key

    raw_json = form.get("_json")
    if isinstance(raw_json, str) and raw_json.strip():
        parsed = json.loads(raw_json)
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("expected object", raw_json, 0)
        profile.update(parsed)
    else:
        for k, v in form.items():
            if k not in _INTERNAL_FORM_KEYS and isinstance(v, str) and v.strip():
                profile[k] = v.strip()
    return profile


def _persist_profile(name: str, profile: dict[str, Any], activate: bool):
    """Save the profile; return an error response on failure, else None."""
    from janus.profile import add_profile  # noqa: PLC0415

    try:
        add_profile(name, profile, activate=activate)
    except ValueError as exc:
        return _error_html(f"✗ Failed to save profile: {escape(str(exc))}")
    except OSError as exc:
        return _error_html(
            f"✗ Failed to save profile: {escape(str(exc))}", status_code=500
        )
    except Exception:
        logger.exception("Unexpected error while saving profile '%s'", name)
        return _error_html(
            "✗ Failed to save profile due to an unexpected error.", status_code=500
        )
    return None


def _schedule_shutdown(server_ref: list) -> None:
    """Stop the server shortly after the save response has been delivered."""
    srv = server_ref[0] if server_ref else None
    if srv is not None:
        loop = asyncio.get_running_loop()
        loop.call_later(0.5, lambda: setattr(srv, "should_exit", True))


def create_app(
    profile_name: str,
    activate: bool = False,
) -> tuple[Starlette, dict[str, Any], list]:
    """Create the profile web app.

    Returns:
        (app, result, server_ref) where result dict is populated with
        {"name", "datasource"} after a successful POST /save, and
        server_ref is a mutable list the start() function appends the
        uvicorn.Server instance into so the save handler can trigger shutdown.
    """
    result: dict[str, Any] = {}
    # Mutable reference so the save handler can reach the server instance
    server_ref: list[uvicorn.Server] = []

    async def index(request: Request):
        return templates.TemplateResponse(
            request,
            "profile_form.html",
            {
                "profile_name": profile_name,
                "datasource_options": get_selectable_datasources(),
            },
        )

    async def save(request: Request):
        form = await request.form()
        ds = (_form_text(form, "datasource") or "").lower()
        name = _form_text(form, "_profile_name") or profile_name
        variant_key = _form_text(form, "_variant")

        if not ds:
            return _error_html("✗ Please select a data source.")
        error = _datasource_error(ds, variant_key)
        if error is not None:
            return error
        try:
            profile = _profile_from_form(form, ds, variant_key)
        except json.JSONDecodeError:
            return _error_html("✗ Invalid JSON.")

        error = _persist_profile(name, profile, activate)
        if error is not None:
            return error
        result.update({"name": name, "datasource": ds})
        _schedule_shutdown(server_ref)

        return HTMLResponse(
            f'<small style="color:var(--pico-color-green-500)">'
            f"✓ Profile <strong>{escape(name)}</strong> saved. You can close this tab.</small>"
        )

    app = Starlette(
        routes=[
            Route("/", index),
            Route("/fields", _fields_endpoint),
            Route("/save", save, methods=["POST"]),
        ]
    )
    return app, result, server_ref  # type: ignore[return-value]


class _ProfileServer(uvicorn.Server):
    """Uvicorn server that calls a hook once the server is ready to accept connections."""

    def __init__(self, config: uvicorn.Config, *, on_ready=None) -> None:
        super().__init__(config)
        self._on_ready = on_ready

    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        if self.started and self._on_ready:
            self._on_ready()


def _free_port() -> int:
    """Find and return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(
    profile_name: str,
    *,
    activate: bool = False,
    port: int = 0,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Start the temporary profile web server and block until saved or Ctrl+C.

    Args:
        profile_name: Name for the new profile.
        activate: Set the profile as active after saving.
        port: Port to bind (0 = auto-select free port).
        open_browser: Auto-open the browser when the server is ready.

    Returns:
        {"name": ..., "datasource": ...} on success, or {} on Ctrl+C.
    """
    actual_port = port if port != 0 else _free_port()
    app, result, server_ref = create_app(profile_name, activate=activate)

    def on_ready():
        url = f"http://localhost:{actual_port}"
        if open_browser:
            import webbrowser  # noqa: PLC0415

            webbrowser.open(url)
        else:
            print(f"Profile form available at {url}", flush=True)  # noqa: T201

    config = uvicorn.Config(
        app, host="127.0.0.1", port=actual_port, log_level="warning"
    )
    server = _ProfileServer(config, on_ready=on_ready)
    server_ref.append(server)

    try:
        server.run()
    except KeyboardInterrupt:
        pass

    return result

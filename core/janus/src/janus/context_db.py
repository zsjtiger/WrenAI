"""Open a live connector for a context project's bound profile.

Used by ``janus context diff`` and ``janus context draft --from-db``. Mirrors
the profile handling of ``janus.cli._build_engine`` (project pin, then the
global active profile, with ``${VAR}`` secrets expanded at connect time) but
returns a bare connector instead of a planning engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from janus.model.data_source import DataSource


class ProjectConnectionError(RuntimeError):
    """The project has no usable connection profile."""


def resolve_project_datasource(project_path: Path) -> DataSource:
    """The data source declared by the project's ``janus_project.yml``."""
    from janus.context import load_project_config  # noqa: PLC0415

    raw = load_project_config(project_path).get("data_source")
    if not isinstance(raw, str) or not raw.strip():
        raise ProjectConnectionError(
            "janus_project.yml has no data_source; cannot choose a connector."
        )
    try:
        return DataSource(raw.strip().lower())
    except ValueError as exc:
        raise ProjectConnectionError(f"unknown data_source '{raw}'") from exc


def open_project_connector(project_path: Path) -> Any:
    """Connect to the database bound to ``project_path``.

    Raises ``ProjectConnectionError`` when no profile is bound or the profile
    does not name a data source.
    """
    from janus.connector.factory import get_connector  # noqa: PLC0415
    from janus.profile import (  # noqa: PLC0415
        MissingSecretError,
        expand_profile_secrets,
        resolve_profile_for_project,
    )

    name, profile = resolve_profile_for_project(project_path)
    if not profile:
        raise ProjectConnectionError(
            "no connection profile is bound to this project. Run "
            "`janus context set-profile <name>` or `janus profile switch <name>`."
        )
    profile = dict(profile)
    ds_str = profile.pop("datasource", None)
    if not ds_str:
        raise ProjectConnectionError(f"profile '{name}' has no datasource")
    try:
        data_source = DataSource(str(ds_str).lower())
    except ValueError as exc:
        raise ProjectConnectionError(f"unknown datasource '{ds_str}'") from exc
    try:
        profile = expand_profile_secrets(profile)
    except MissingSecretError as exc:
        raise ProjectConnectionError(str(exc)) from exc

    info = data_source.get_connection_info(profile)
    return get_connector(data_source, info)

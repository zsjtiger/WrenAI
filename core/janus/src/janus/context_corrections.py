"""Correction queue: agents propose MDL changes, a person approves them.

A proposal is written to ``knowledge/corrections/<id>.yml`` with
``status: pending``. Nothing in ``models/`` changes until ``approve_correction``
merges the proposed fields into the model's ``metadata.yml``, validates the
project, and marks the proposal ``applied``. A failed validation restores the
original file and leaves the proposal pending. Applied and rejected proposals
stay on disk as an audit trail.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CORRECTIONS_DIR = Path("knowledge") / "corrections"
PENDING = "pending"
APPLIED = "applied"
REJECTED = "rejected"

#: Fields a correction may never change: the model's identity is its name and
#: its physical source, which only a person editing the project should change.
_PROTECTED_FIELDS = frozenset({"name", "table_reference", "ref_sql"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "correction"


def _corrections_dir(project_path: Path) -> Path:
    return project_path / CORRECTIONS_DIR


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a mapping")
    return data


def _find(project_path: Path, correction_id: str) -> Path:
    path = _corrections_dir(project_path) / f"{correction_id}.yml"
    if not path.exists():
        raise ValueError(f"no correction named '{correction_id}'")
    return path


def _model_metadata_path(project_path: Path, model_name: str) -> Path:
    from janus.context import load_models  # noqa: PLC0415

    for model in load_models(project_path):
        if model.get("name") == model_name:
            source_dir = model.get("_source_dir")
            if not source_dir:
                raise ValueError(
                    "corrections need a project with models/<name>/metadata.yml"
                )
            return project_path / "models" / source_dir / "metadata.yml"
    raise ValueError(f"model '{model_name}' not found in the project")


def propose_correction(
    project_path: Path,
    *,
    model: str,
    problem: str,
    proposed_change: str,
) -> str:
    """Record a pending correction. Returns the correction id.

    ``proposed_change`` is YAML: a mapping of model fields to set. Fields in
    ``_PROTECTED_FIELDS`` are refused, and the model must already exist.
    """
    _model_metadata_path(project_path, model)  # raises if the model is unknown
    try:
        change = yaml.safe_load(proposed_change)
    except yaml.YAMLError as exc:
        raise ValueError(f"proposed_change is not valid YAML: {exc}") from exc
    if not isinstance(change, dict) or not change:
        raise ValueError("proposed_change must be a non-empty YAML mapping")
    blocked = sorted(_PROTECTED_FIELDS & set(change))
    if blocked:
        raise ValueError(f"proposed_change may not set {', '.join(blocked)}")
    if not problem.strip():
        raise ValueError("problem must describe what is wrong")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    correction_id = f"{stamp}-{_slug(model)}"
    path = _corrections_dir(project_path) / f"{correction_id}.yml"
    counter = 2
    while path.exists():
        correction_id = f"{stamp}-{_slug(model)}-{counter}"
        path = _corrections_dir(project_path) / f"{correction_id}.yml"
        counter += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": correction_id,
        "status": PENDING,
        "model": model,
        "problem": problem.strip(),
        "proposed_change": change,
        "created_at": _now(),
    }
    path.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return correction_id


def list_corrections(project_path: Path, status: str | None = None) -> list[dict]:
    directory = _corrections_dir(project_path)
    if not directory.is_dir():
        return []
    records = []
    for path in sorted(directory.glob("*.yml")):
        record = _load(path)
        if status is None or record.get("status") == status:
            records.append(record)
    return records


def reject_correction(project_path: Path, correction_id: str, reason: str) -> None:
    path = _find(project_path, correction_id)
    record = _load(path)
    if record.get("status") != PENDING:
        raise ValueError(f"correction '{correction_id}' is {record.get('status')}")
    record.update(status=REJECTED, rejected_at=_now(), reject_reason=reason)
    path.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def approve_correction(project_path: Path, correction_id: str) -> Path:
    """Merge a pending correction into its model and mark it applied.

    Returns the edited ``metadata.yml``. Raises ``ValueError`` and restores the
    original files when the merged project fails validation.
    """
    from janus.context import validate_project  # noqa: PLC0415

    path = _find(project_path, correction_id)
    record = _load(path)
    if record.get("status") != PENDING:
        raise ValueError(f"correction '{correction_id}' is {record.get('status')}")

    meta_path = _model_metadata_path(project_path, record["model"])
    original_meta = meta_path.read_text(encoding="utf-8")
    original_record = path.read_text(encoding="utf-8")

    model = yaml.safe_load(original_meta) or {}
    for key, value in dict(record["proposed_change"]).items():
        if key == "properties" and isinstance(value, dict):
            merged = dict(model.get("properties") or {})
            merged.update(value)
            model["properties"] = merged
        else:
            model[key] = value
    meta_path.write_text(
        yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    record.update(status=APPLIED, applied_at=_now())
    path.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    errors = [e for e in validate_project(project_path) if e.level == "error"]
    if errors:
        meta_path.write_text(original_meta, encoding="utf-8")
        path.write_text(original_record, encoding="utf-8")
        raise ValueError(
            "validation failed after applying the correction; nothing was changed: "
            + "; ".join(str(e) for e in errors)
        )
    return meta_path

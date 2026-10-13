"""Characterization tests for validate_project branches that had no coverage.

These pin the current level, path and message for each check so the function
can be split into smaller validators without changing what users see.
"""

from __future__ import annotations

from pathlib import Path

from janus.context import validate_project


def _v2(tmp_path: Path, schema_version: int = 2) -> Path:
    (tmp_path / "janus_project.yml").write_text(
        f"schema_version: {schema_version}\nname: test\ndata_source: postgres\n"
    )
    return tmp_path


def _model(tmp_path: Path, name: str, body: str) -> None:
    d = tmp_path / "models" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.yml").write_text(body)


def _one(errors, *, level: str, path: str, message: str):
    matches = [
        e
        for e in errors
        if e.level == level and e.path == path and e.message == message
    ]
    assert len(matches) == 1, [(e.level, e.path, e.message) for e in errors]


def test_missing_project_file_reports_not_found(tmp_path):
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="janus_project.yml",
        message="'janus_project.yml' not found or empty",
    )


def test_non_integer_schema_version_is_reported_and_stops(tmp_path):
    (tmp_path / "janus_project.yml").write_text(
        "schema_version: abc\nname: test\ndata_source: postgres\n"
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="janus_project.yml",
        message="schema_version must be an integer, got 'abc'",
    )
    assert len(errors) == 1


def test_table_reference_without_table_warns(tmp_path):
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  catalog: main\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="models/orders/metadata.yml > orders",
        message="table_reference.table is empty",
    )


def test_model_without_columns_warns(tmp_path):
    _v2(tmp_path)
    _model(tmp_path, "orders", "name: orders\ntable_reference:\n  table: orders\n")
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="models/orders/metadata.yml > orders",
        message="model has no columns",
    )


def test_column_without_type_warns(tmp_path):
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\ncolumns:\n  - name: id\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="models/orders/metadata.yml > orders > id",
        message="column missing 'type'",
    )


def test_non_string_primary_key_is_an_error(tmp_path):
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\n"
        "columns:\n  - name: id\n    type: INTEGER\n"
        "primary_key: 123\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="models/orders/metadata.yml > orders",
        message="primary_key must be a non-empty string or list of non-empty strings",
    )


def test_model_dialect_on_schema_v2_warns(tmp_path):
    _v2(tmp_path, schema_version=2)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\ndialect: postgres\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="models/orders/metadata.yml > orders",
        message="'dialect' field requires schema_version >= 3 (current: 2)",
    )


def test_unknown_model_dialect_is_an_error(tmp_path):
    _v2(tmp_path, schema_version=3)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\ndialect: nosuch\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="models/orders/metadata.yml > orders",
        message="unknown dialect 'nosuch'",
    )


def test_relationship_to_unknown_model_is_an_error(tmp_path):
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    (tmp_path / "relationships.yml").write_text(
        "relationships:\n  - name: r1\n    models: [orders, ghost]\n"
        "    join_type: MANY_TO_ONE\n    condition: orders.id = ghost.id\n"
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="relationships > r1",
        message="references unknown model 'ghost'",
    )


def test_relationship_missing_condition_and_join_type_warn(tmp_path):
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    (tmp_path / "relationships.yml").write_text(
        "relationships:\n  - name: r1\n    models: [orders, orders]\n"
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="relationships > r1",
        message="missing join condition",
    )
    _one(
        errors,
        level="warning",
        path="relationships > r1",
        message="missing join_type",
    )


def _cube(tmp_path: Path, body: str) -> None:
    _v2(tmp_path)
    _model(
        tmp_path,
        "orders",
        "name: orders\ntable_reference:\n  table: orders\n"
        "columns:\n  - name: id\n    type: INTEGER\n",
    )
    d = tmp_path / "cubes" / "revenue"
    d.mkdir(parents=True)
    (d / "metadata.yml").write_text(body)


def test_cube_without_measures_warns(tmp_path):
    _cube(tmp_path, "name: revenue\nbase_object: orders\n")
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="warning",
        path="cubes/revenue/metadata.yml > revenue",
        message="cube has no measures",
    )


def test_hierarchy_level_must_be_a_declared_dimension(tmp_path):
    _cube(
        tmp_path,
        "name: revenue\nbase_object: orders\n"
        "measures:\n  - name: total\n    expression: SUM(id)\n    type: DOUBLE\n"
        "hierarchies:\n  time: [nope]\n",
    )
    errors = validate_project(tmp_path)
    _one(
        errors,
        level="error",
        path="cubes/revenue/metadata.yml > revenue > hierarchies.time",
        message="references unknown dimension 'nope'",
    )

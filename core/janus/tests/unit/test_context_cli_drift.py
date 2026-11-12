"""CLI surface for diff, draft and review, run against a real DuckDB database.

The profile lookup is pointed at the test database; everything else (the
connector, the diff, the drafts and the queue) runs for real.
"""

from __future__ import annotations

import json

import pytest
import yaml
from typer.testing import CliRunner

from janus.context_cli import context_app
from janus.context_corrections import list_corrections, propose_correction
from tests.unit.conftest import model_dict, shop_connection_info

pytestmark = pytest.mark.unit

runner = CliRunner()


@pytest.fixture
def bound_profile(monkeypatch, shop_dir):
    """Bind the project to the shop database through a duckdb profile."""
    profile = {"datasource": "duckdb", **shop_connection_info(shop_dir)}
    monkeypatch.setattr(
        "janus.profile.resolve_profile_for_project",
        lambda project: ("shop", dict(profile)),
    )
    return profile


@pytest.fixture
def in_sync_project(make_project):
    return make_project(
        [
            model_dict(
                "customers",
                "customers",
                [("id", "INTEGER"), ("name", "VARCHAR")],
                primary_key="id",
                properties={"certified": "true"},
            ),
            model_dict(
                "orders",
                "orders",
                [
                    ("order_id", "INTEGER"),
                    ("cust_id", "INTEGER"),
                    ("amount", "DECIMAL(10,2)"),
                ],
                primary_key="order_id",
            ),
        ]
    )


def test_diff_exits_zero_when_in_sync(in_sync_project, bound_profile):
    result = runner.invoke(context_app, ["diff", "--path", str(in_sync_project)])
    assert result.exit_code == 0, result.output
    assert "no drift" in result.output


def test_diff_exits_one_and_lists_drift(in_sync_project, bound_profile):
    meta = in_sync_project / "models" / "orders" / "metadata.yml"
    data = yaml.safe_load(meta.read_text())
    data["columns"].append({"name": "shipped_at", "type": "DATE"})
    meta.write_text(yaml.safe_dump(data))

    result = runner.invoke(
        context_app, ["diff", "--path", str(in_sync_project), "--json"]
    )
    assert result.exit_code == 1, result.output
    report = json.loads(result.output)
    assert report["has_drift"] is True
    assert {"kind": "column_missing", "model": "orders"}.items() <= report["items"][
        0
    ].items()


def test_diff_exits_two_without_a_bound_profile(in_sync_project, monkeypatch):
    monkeypatch.setattr(
        "janus.profile.resolve_profile_for_project", lambda project: (None, {})
    )
    result = runner.invoke(context_app, ["diff", "--path", str(in_sync_project)])
    assert result.exit_code == 2
    assert "no connection profile" in result.output


def test_draft_from_db_then_apply(make_project, bound_profile):
    project = make_project([])
    result = runner.invoke(context_app, ["draft", "--from-db", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert "Drafted 2 model(s)" in result.output

    listing = runner.invoke(context_app, ["draft", "--path", str(project)])
    assert "customers" in listing.output and "orders" in listing.output

    applied = runner.invoke(
        context_app, ["draft", "apply", "customers", "--path", str(project)]
    )
    assert applied.exit_code == 0, applied.output
    assert (project / "models" / "customers" / "metadata.yml").exists()


def test_review_lists_approves_and_rejects(in_sync_project):
    first = propose_correction(
        in_sync_project,
        model="orders",
        problem="amount is gross",
        proposed_change="description: Net amount",
    )
    second = propose_correction(
        in_sync_project,
        model="customers",
        problem="name is ambiguous",
        proposed_change="description: Display name",
    )

    listing = runner.invoke(context_app, ["review", "--path", str(in_sync_project)])
    assert first in listing.output and second in listing.output

    approved = runner.invoke(
        context_app, ["review", "approve", first, "--path", str(in_sync_project)]
    )
    assert approved.exit_code == 0, approved.output
    meta = yaml.safe_load(
        (in_sync_project / "models" / "orders" / "metadata.yml").read_text()
    )
    assert meta["description"] == "Net amount"

    rejected = runner.invoke(
        context_app,
        [
            "review",
            "reject",
            second,
            "--reason",
            "not needed",
            "--path",
            str(in_sync_project),
        ],
    )
    assert rejected.exit_code == 0, rejected.output
    assert [r["id"] for r in list_corrections(in_sync_project, "pending")] == []


def test_show_marks_certified_models(in_sync_project):
    result = runner.invoke(context_app, ["show", "--path", str(in_sync_project)])
    assert result.exit_code == 0, result.output
    lines = {
        line.split("(")[0].strip(): line
        for line in result.output.splitlines()
        if "(" in line
    }
    assert lines["customers"].rstrip().endswith("certified")
    assert "certified" not in lines["orders"]

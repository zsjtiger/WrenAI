"""The correction queue: propose, review, approve and reject."""

from __future__ import annotations

import pytest
import yaml

from janus.context_corrections import (
    approve_correction,
    list_corrections,
    propose_correction,
    reject_correction,
)
from tests.unit.conftest import model_dict

pytestmark = pytest.mark.unit


@pytest.fixture
def project(make_project):
    return make_project(
        [
            model_dict(
                "orders",
                "orders",
                [("order_id", "INTEGER"), ("amount", "DECIMAL(10,2)")],
                primary_key="order_id",
            )
        ]
    )


def _meta(project):
    return yaml.safe_load((project / "models" / "orders" / "metadata.yml").read_text())


def test_propose_queues_a_pending_record_without_touching_models(project):
    before = (project / "models" / "orders" / "metadata.yml").read_text()

    cid = propose_correction(
        project,
        model="orders",
        problem="amount is gross, not net",
        proposed_change="description: Order amount after refunds",
    )

    assert (project / "knowledge" / "corrections" / f"{cid}.yml").exists()
    pending = list_corrections(project, "pending")
    assert [r["id"] for r in pending] == [cid]
    assert pending[0]["proposed_change"] == {
        "description": "Order amount after refunds"
    }
    assert (project / "models" / "orders" / "metadata.yml").read_text() == before


@pytest.mark.parametrize("field", ["name", "table_reference", "ref_sql"])
def test_protected_fields_are_refused(project, field):
    with pytest.raises(ValueError, match="may not set"):
        propose_correction(
            project,
            model="orders",
            problem="p",
            proposed_change=f"{field}: something",
        )


def test_unknown_model_is_refused(project):
    with pytest.raises(ValueError, match="not found"):
        propose_correction(
            project, model="ghost", problem="p", proposed_change="description: x"
        )


def test_approve_merges_into_metadata_and_marks_applied(project):
    cid = propose_correction(
        project,
        model="orders",
        problem="needs a description",
        proposed_change="description: Net order amount\nproperties:\n  owner: finance",
    )

    approve_correction(project, cid)

    meta = _meta(project)
    assert meta["description"] == "Net order amount"
    assert meta["properties"]["owner"] == "finance"
    assert meta["primary_key"] == "order_id"  # untouched fields survive
    record = yaml.safe_load(
        (project / "knowledge" / "corrections" / f"{cid}.yml").read_text()
    )
    assert record["status"] == "applied"
    assert "applied_at" in record


def test_an_applied_correction_cannot_be_applied_again(project):
    cid = propose_correction(
        project, model="orders", problem="p", proposed_change="description: x"
    )
    approve_correction(project, cid)
    with pytest.raises(ValueError, match="applied"):
        approve_correction(project, cid)


def test_reject_records_the_reason_and_blocks_approval(project):
    cid = propose_correction(
        project, model="orders", problem="p", proposed_change="description: x"
    )
    reject_correction(project, cid, "not a real problem")

    record = yaml.safe_load(
        (project / "knowledge" / "corrections" / f"{cid}.yml").read_text()
    )
    assert record["status"] == "rejected"
    assert record["reject_reason"] == "not a real problem"
    assert "description" not in _meta(project)
    with pytest.raises(ValueError, match="rejected"):
        approve_correction(project, cid)


def test_invalid_result_rolls_back_and_stays_pending(project):
    cid = propose_correction(
        project,
        model="orders",
        problem="bad certification value",
        proposed_change='properties:\n  certified: "maybe"',
    )
    original = (project / "models" / "orders" / "metadata.yml").read_text()

    with pytest.raises(ValueError, match="validation failed"):
        approve_correction(project, cid)

    assert (project / "models" / "orders" / "metadata.yml").read_text() == original
    record = yaml.safe_load(
        (project / "knowledge" / "corrections" / f"{cid}.yml").read_text()
    )
    assert record["status"] == "pending"


def test_propose_tool_is_absent_without_allow_write(project):
    from janus.mcp_server import ServeContext, build_server  # noqa: PLC0415

    ctx = ServeContext(project=project, engine=None, allow_write=False, no_connect=True)
    tools = build_server(ctx)._tool_manager._tools
    assert "propose_correction" not in tools


def test_propose_tool_queues_a_correction_with_allow_write(project):
    from janus.mcp_server import ServeContext, build_server  # noqa: PLC0415

    ctx = ServeContext(project=project, engine=None, allow_write=True, no_connect=True)
    tool = build_server(ctx)._tool_manager._tools["propose_correction"].fn
    result = tool(
        model="orders",
        problem="amount is gross",
        proposed_change="description: Net amount",
    )
    assert result == {"id": result["id"], "status": "pending"}
    assert [r["id"] for r in list_corrections(project, "pending")] == [result["id"]]
    assert "description" not in _meta(project)

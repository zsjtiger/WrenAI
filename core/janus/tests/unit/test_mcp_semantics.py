"""MCP access to terms, display names, and attributes."""

from __future__ import annotations

import pytest
import yaml

from janus.mcp_server import ServeContext, build_server, read_attributes
from tests.unit.conftest import model_dict

pytestmark = pytest.mark.unit


def _ctx(project, allow_write=False):
    return ServeContext(
        project=project, engine=None, allow_write=allow_write, no_connect=True
    )


def _tool(project, name, allow_write=False):
    return build_server(_ctx(project, allow_write))._tool_manager._tools[name].fn


@pytest.fixture
def project(make_project):
    model = model_dict(
        "orders",
        "orders",
        [("order_id", "INTEGER"), ("cust_id", "INTEGER")],
        primary_key="order_id",
        properties={"term": "Order", "aliases": "Purchase, Sale"},
    )
    model["columns"][1]["properties"] = {"display_name": "Customer ID"}
    return make_project([model])


def test_describe_model_returns_term_aliases_and_display_names(project):
    described = _tool(project, "describe_model")("orders")
    assert described["term"] == "Order"
    assert described["aliases"] == ["Purchase", "Sale"]
    cust = next(c for c in described["columns"] if c["name"] == "cust_id")
    assert cust["display_name"] == "Customer ID"
    order = next(c for c in described["columns"] if c["name"] == "order_id")
    assert order["display_name"] is None


def test_list_models_reports_the_term(project):
    listed = _tool(project, "list_models")()
    assert listed["models"][0]["term"] == "Order"


def test_list_attributes_reads_the_knowledge_directory(project):
    attr_dir = project / "knowledge" / "attributes"
    attr_dir.mkdir(parents=True)
    (attr_dir / "orders.yml").write_text(
        yaml.safe_dump(
            {
                "model": "orders",
                "attributes": [
                    {
                        "name": "total_amount",
                        "expression": "sum(amount)",
                        "kind": "aggregate",
                        "occurrences": 3,
                        "status": "suggested",
                    },
                ],
            }
        )
    )
    result = _tool(project, "list_attributes")()
    assert result["attributes"] == [
        {
            "model": "orders",
            "name": "total_amount",
            "expression": "sum(amount)",
            "kind": "aggregate",
            "occurrences": 3,
            "status": "suggested",
        }
    ]
    assert _tool(project, "list_attributes")(model="orders")["attributes"] == result["attributes"]
    assert _tool(project, "list_attributes")(model="customers")["attributes"] == []


def test_list_attributes_is_empty_without_the_directory(project):
    assert _tool(project, "list_attributes")() == {"attributes": []}


def test_model_names_are_validated_before_touching_the_file_system(project):
    with pytest.raises(ValueError, match="invalid model name"):
        read_attributes(project, "../janus_project")


def test_list_attributes_is_available_without_allow_write(project):
    tools = build_server(_ctx(project, allow_write=False))._tool_manager._tools
    assert "list_attributes" in tools
    assert "propose_correction" not in tools

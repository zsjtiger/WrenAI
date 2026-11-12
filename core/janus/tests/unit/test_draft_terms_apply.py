"""Terms and attributes flow into the model when a draft is applied."""

from __future__ import annotations

import pytest
import yaml
from typer.testing import CliRunner

from janus.connector.factory import get_connector
from janus.context import load_models
from janus.context_cli import context_app
from janus.context_draft import apply_draft, generate_drafts
from janus.memory.markdown import write_query_markdown
from janus.model.data_source import DataSource
from tests.unit.conftest import shop_connection_info

pytestmark = pytest.mark.unit


@pytest.fixture
def connector(shop_dir):
    info = DataSource.duckdb.get_connection_info(shop_connection_info(shop_dir))
    conn = get_connector(DataSource.duckdb, info)
    yield conn
    conn.close()


@pytest.fixture
def drafted(make_project, connector):
    """A project with drafts for customers and orders, and some confirmed queries."""
    project = make_project([])
    generate_drafts(project, connector, DataSource.duckdb)
    write_query_markdown(
        project, "revenue", "SELECT SUM(amount) FROM orders WHERE cust_id = 1"
    )
    write_query_markdown(
        project, "revenue again", "SELECT SUM(amount) FROM orders WHERE cust_id = 1"
    )
    runner = CliRunner()
    assert runner.invoke(context_app, ["terms", "--path", str(project)]).exit_code == 0
    assert (
        runner.invoke(
            context_app,
            ["attributes", "--path", str(project), "--min-occurrences", "2"],
        ).exit_code
        == 0
    )
    return project


def _draft_meta(project, name):
    return project / "draft" / "models" / name / "metadata.yml"


def test_apply_merges_term_aliases_and_display_names(drafted):
    apply_draft(drafted, "orders")
    meta = yaml.safe_load((drafted / "models" / "orders" / "metadata.yml").read_text())
    assert meta["properties"]["term"] == "Order"
    col = next(c for c in meta["columns"] if c["name"] == "cust_id")
    assert col["properties"]["display_name"] == "Customer ID"
    assert "draft" not in meta["properties"]


def test_apply_writes_confirmed_attributes_to_knowledge(drafted):
    apply_draft(drafted, "orders")
    attrs = yaml.safe_load(
        (drafted / "knowledge" / "attributes" / "orders.yml").read_text()
    )
    names = {a["name"] for a in attrs["attributes"]}
    assert "total_amount" in names
    assert attrs["model"] == "orders"


def test_existing_values_in_the_draft_are_not_overwritten(drafted):
    meta_path = _draft_meta(drafted, "orders")
    meta = yaml.safe_load(meta_path.read_text())
    meta["properties"]["term"] = "Purchase"
    meta_path.write_text(yaml.safe_dump(meta))
    apply_draft(drafted, "orders")
    applied = yaml.safe_load(
        (drafted / "models" / "orders" / "metadata.yml").read_text()
    )
    assert applied["properties"]["term"] == "Purchase"


def test_rejected_attributes_are_not_written(drafted):
    attrs_path = drafted / "draft" / "attributes.yml"
    data = yaml.safe_load(attrs_path.read_text())
    for attr in data["attributes"]:
        attr["status"] = "rejected"
    attrs_path.write_text(yaml.safe_dump(data))
    apply_draft(drafted, "orders")
    assert not (drafted / "knowledge" / "attributes" / "orders.yml").exists()


def test_failed_apply_restores_the_draft_and_writes_no_attributes(drafted):
    meta_path = _draft_meta(drafted, "orders")
    meta = yaml.safe_load(meta_path.read_text())
    meta["properties"]["certified"] = "maybe"  # fails validation
    meta_path.write_text(yaml.safe_dump(meta))
    before = meta_path.read_text()

    with pytest.raises(ValueError, match="validation failed"):
        apply_draft(drafted, "orders")

    assert meta_path.read_text() == before  # no merged term left in the draft
    assert not (drafted / "knowledge" / "attributes" / "orders.yml").exists()


def test_failed_apply_restores_a_pre_existing_attribute_file(drafted):
    attr_path = drafted / "knowledge" / "attributes" / "orders.yml"
    attr_path.parent.mkdir(parents=True)
    attr_path.write_text("model: orders\nattributes: []\n")
    meta_path = _draft_meta(drafted, "orders")
    meta = yaml.safe_load(meta_path.read_text())
    meta["properties"]["certified"] = "maybe"
    meta_path.write_text(yaml.safe_dump(meta))

    with pytest.raises(ValueError):
        apply_draft(drafted, "orders")

    assert attr_path.read_text() == "model: orders\nattributes: []\n"


def test_terms_cover_drafts_before_they_are_applied(drafted):
    data = yaml.safe_load((drafted / "draft" / "terms.yml").read_text())
    assert {t["model"] for t in data["terms"]} == {"customers", "orders"}
    assert load_models(drafted) == []  # the drafts are not in models/ yet

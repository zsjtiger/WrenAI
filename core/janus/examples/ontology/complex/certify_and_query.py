"""Certify the core star, then run queries with provenance.

fact_sales, dim_product, and dim_store are certified; dim_customer and the
account and company models are not. Shows the provenance of a multi-hop query
(which models it read and whether each is certified), and the same query with
require_certified on.

Usage: python certify_and_query.py <project_dir> <warehouse_dir>
"""

import base64
import json
import sys
from pathlib import Path

import yaml

from janus.config import JanusConfig
from janus.context import build_json
from janus.engine import JanusEngine
from janus.model.data_source import DataSource
from janus.model.error import JanusError

project = Path(sys.argv[1])
warehouse = sys.argv[2]

for name in ("fact_sales", "dim_product", "dim_store"):
    meta = project / "models" / name / "metadata.yml"
    data = yaml.safe_load(meta.read_text(encoding="utf-8"))
    data.setdefault("properties", {})["certified"] = "true"
    meta.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("certified: fact_sales, dim_product, dim_store")

manifest = base64.b64encode(json.dumps(build_json(project)).encode()).decode()
conn_info = {"url": warehouse, "format": "duckdb"}

multi_hop = (
    "SELECT co.company_name, SUM(f.net_amount) AS revenue "
    "FROM fact_sales f "
    "JOIN dim_customer c ON f.customer_key = c.customer_key "
    "JOIN accounts a ON c.account_id = a.id "
    "JOIN companies co ON a.company_id = co.company_id "
    "GROUP BY co.company_name ORDER BY co.company_name"
)


def run(sql: str, config: JanusConfig, label: str) -> None:
    print(f"\n-- {label}")
    with JanusEngine(manifest, DataSource.duckdb, conn_info, fallback=False,
                     config=config) as engine:
        try:
            table, models, _ = engine.query_with_provenance(sql, 50)
        except JanusError as exc:
            reason = next((line for line in str(exc).splitlines() if "not certified" in line),
                          str(exc).splitlines()[0])
            print("refused:", reason.strip())
            return
    print("rows:", table.num_rows)
    print("models read:", ", ".join(f"{m}={'certified' if c else 'uncertified'}"
                                    for m, c in sorted(models.items())))
    if not all(models.values()):
        print("warning: uncertified models in this query")


run(multi_hop, JanusConfig(), "multi-hop revenue, warnings on")
run(multi_hop, JanusConfig(require_certified=True), "multi-hop revenue, require_certified on")
run("SELECT p.category, SUM(f.net_amount) FROM fact_sales f "
    "JOIN dim_product p ON f.product_key = p.product_key GROUP BY p.category",
    JanusConfig(require_certified=True), "revenue by category, all certified")

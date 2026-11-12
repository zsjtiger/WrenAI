"""Certification and provenance on the demo project.

Certifies customers, leaves orders uncertified, then shows:
  1. a query over orders: provenance plus an uncertified warning;
  2. the same query with require_certified on: refused at planning time.

Usage: python governance_demo.py <project_dir> <warehouse_dir>
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

meta = project / "models" / "customers" / "metadata.yml"
data = yaml.safe_load(meta.read_text(encoding="utf-8"))
data.setdefault("properties", {})["certified"] = "true"
meta.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("certified: customers")

manifest = base64.b64encode(json.dumps(build_json(project)).encode()).decode()
conn_info = {"url": warehouse, "format": "duckdb"}
sql = "SELECT order_id, amount FROM orders WHERE status = 'shipped'"


def run(config: JanusConfig, label: str) -> None:
    print(f"\n-- {label}")
    with JanusEngine(manifest, DataSource.duckdb, conn_info, fallback=False,
                     config=config) as engine:
        try:
            table, models, _ = engine.query_with_provenance(sql, 10)
        except JanusError as exc:
            print("refused:", exc)
            return
    print("rows:", table.num_rows)
    print("provenance: models", sorted(models), "certified", models)
    if not all(models.values()):
        print("warning: model 'orders' is not certified")


run(JanusConfig(), "orders is uncertified, require_certified off")
run(JanusConfig(require_certified=True), "require_certified on")

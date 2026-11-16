#!/usr/bin/env bash
# Query a database through the janus MCP server, end to end, with no
# external database: a DuckDB file is the warehouse.
#
#   ./run_demo.sh                                              # `janus` on PATH
#   JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh    # from a source checkout
#
# Everything is written under ./work/ (warehouse, profile, project).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
JANUS="${JANUS:-janus}"
PYTHON="${PYTHON:-python3}"
WORK="$HERE/work"

step() { printf '\n== %s ==\n' "$1"; }

"$PYTHON" -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$WORK"
mkdir -p "$WORK/home" "$WORK/warehouse"
export JANUS_HOME="$WORK/home"
export JANUS_PROJECT_HOME="$WORK/project"
PROJECT="$WORK/project"

step "1. Warehouse (DuckDB file: customers, orders)"
"$PYTHON" "$HERE/make_warehouse.py" "$WORK/warehouse/warehouse.duckdb"

step "2. Connection profile"
cat > "$JANUS_HOME/profiles.yml" <<YAML
active: demo
profiles:
  demo:
    datasource: duckdb
    url: $WORK/warehouse
    format: duckdb
YAML

step "3. Project and models generated from the database"
$JANUS context init --path "$PROJECT" --empty >/dev/null
"$PYTHON" - "$PROJECT/janus_project.yml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(
    re.sub(r"(?m)^data_source:.*$", "data_source: duckdb", text)
)
PY
$JANUS context draft --from-db --path "$PROJECT"
$JANUS context draft --path "$PROJECT"
for model in customers orders; do
  $JANUS context draft apply "$model" --path "$PROJECT"
done
$JANUS context build --path "$PROJECT"

step "4. Query through the MCP server (stdio)"
"$PYTHON" "$HERE/mcp_client.py" "$PROJECT"

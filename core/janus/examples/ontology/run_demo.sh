#!/usr/bin/env bash
# Walk through the ontology operations on the demo warehouse, step by step.
#
#   ./run_demo.sh                           # uses the `janus` command on PATH
#   JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh   # from a source checkout
#
# Everything is written under ./work/ (the project, a profile, the warehouse).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
JANUS="${JANUS:-janus}"
PYTHON="${PYTHON:-python3}"
WORK="$HERE/work"

step() { printf '\n== %s ==\n' "$1"; }

# Start from a clean work directory (only the demo's own folder is touched).
"$PYTHON" -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$WORK"
mkdir -p "$WORK/home" "$WORK/warehouse"
export JANUS_HOME="$WORK/home"
export JANUS_PROJECT_HOME="$WORK/project"
PROJECT="$WORK/project"

step "1. Demo warehouse (no foreign keys declared)"
"$PYTHON" "$HERE/make_warehouse.py" "$WORK/warehouse/warehouse.duckdb"

step "2. Connection profile and an empty project"
cat > "$JANUS_HOME/profiles.yml" <<EOF
active: demo
profiles:
  demo:
    datasource: duckdb
    url: $WORK/warehouse
    format: duckdb
EOF
$JANUS context init --path "$PROJECT" --empty >/dev/null
"$PYTHON" - "$PROJECT/janus_project.yml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(re.sub(r"(?m)^data_source:.*$", "data_source: duckdb", text))
PY
echo "project: $PROJECT"

step "3. Draft models for the unmodeled tables"
$JANUS context draft --from-db --schema main --path "$PROJECT"

step "4. Infer undeclared foreign keys and bridge tables"
$JANUS context infer-fks --path "$PROJECT"

step "5. Business terms and column display names"
$JANUS context terms --path "$PROJECT"

step "6. Confirmed query history, then mined SQL attributes"
"$PYTHON" "$HERE/write_history.py" "$PROJECT"
$JANUS context attributes --path "$PROJECT" --min-occurrences 2

step "7. Promote the drafts into models/ (parents before children)"
for model in regions customers dim_products orders order_items customer_regions; do
  $JANUS context draft apply "$model" --path "$PROJECT"
done

step "8. Build, validate, and check the ontology against the database"
$JANUS context build --path "$PROJECT" >/dev/null
$JANUS context validate --path "$PROJECT" | tail -2 || true
$JANUS context diff --schema main --path "$PROJECT"

step "9. Query through the semantic layer"
$JANUS --sql "SELECT c.name, SUM(o.amount) AS revenue FROM orders o JOIN customers c ON o.cust_id = c.id WHERE o.status = 'shipped' GROUP BY c.name ORDER BY c.name"

step "10. Certification and provenance"
"$PYTHON" "$HERE/governance_demo.py" "$PROJECT" "$WORK/warehouse"
$JANUS context build --path "$PROJECT" >/dev/null

step "11. Agent correction, reviewed and approved"
CID="$("$PYTHON" "$HERE/review_demo.py" "$PROJECT" | tail -1)"
$JANUS context review --path "$PROJECT"
$JANUS context review approve "$CID" --path "$PROJECT"
$JANUS context build --path "$PROJECT" >/dev/null
echo "orders description now: $(grep '^description:' "$PROJECT/models/orders/metadata.yml")"

printf '\nDone. The project is in %s\n' "$PROJECT"

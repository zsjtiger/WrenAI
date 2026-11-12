#!/usr/bin/env bash
# The complex ontology demo: a two-schema retail star, with a legacy duplicate,
# a cross-schema reference, a pure bridge table, and an ambiguous key that a
# person has to decide. Ends with certification, reviewed corrections, and a
# failed apply that is rolled back.
#
#   ./run_complex_demo.sh
#   JANUS="python -m janus.cli" PYTHON=python ./run_complex_demo.sh   # source checkout
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
JANUS="${JANUS:-janus}"
PYTHON="${PYTHON:-python3}"
WORK="$HERE/work"
PROJECT="$WORK/project"

step() { printf '\n== %s ==\n' "$1"; }

"$PYTHON" -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$WORK"
mkdir -p "$WORK/home"
export JANUS_HOME="$WORK/home"
export JANUS_PROJECT_HOME="$PROJECT"

step "1. Warehouse: sales and crm schemas"
"$PYTHON" "$HERE/make_retail_warehouse.py" "$WORK/warehouse/retail.duckdb"

step "2. Profile and an empty project"
cat > "$JANUS_HOME/profiles.yml" <<EOF
active: retail
profiles:
  retail:
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

step "3. Draft every table, one schema at a time"
$JANUS context draft --from-db --schema sales --path "$PROJECT"
$JANUS context draft --from-db --schema crm --path "$PROJECT"

step "4. Infer foreign keys: cross-schema, prefixed names, bridge, and a tie"
$JANUS context infer-fks --path "$PROJECT"

step "5. Terms and mined attributes from eight confirmed queries"
"$PYTHON" "$HERE/write_retail_history.py" "$PROJECT"
$JANUS context terms --path "$PROJECT" >/dev/null
$JANUS context attributes --path "$PROJECT" --min-occurrences 2 --top-n 4

step "6. A person resolves the tie: the current companies table, not the legacy copy"
"$PYTHON" "$HERE/declare_relationship.py" "$PROJECT"

step "7. Promote the drafts (order does not matter: relationships wait for both ends)"
for model in dim_date dim_store dim_product dim_promo dim_customer accounts companies company \
             fact_sales bridge_promo_product; do
  $JANUS context draft apply "$model" --path "$PROJECT"
done

step "8. Build, validate, and diff each schema against the warehouse"
$JANUS context build --path "$PROJECT" >/dev/null
$JANUS context validate --path "$PROJECT" >/dev/null || true
$JANUS context diff --schema sales --path "$PROJECT" || true
$JANUS context diff --schema crm --path "$PROJECT" || true

step "9. Queries through the semantic layer"
$JANUS --sql "SELECT p.category, SUM(f.net_amount) AS revenue FROM fact_sales f JOIN dim_product p ON f.product_key = p.product_key GROUP BY p.category ORDER BY p.category"
$JANUS --sql "SELECT pr.promo_name, p.product_name FROM bridge_promo_product b JOIN dim_promo pr ON b.promo_id = pr.promo_id JOIN dim_product p ON b.product_key = p.product_key ORDER BY 1, 2"

step "10. Certification, provenance, and require_certified"
"$PYTHON" "$HERE/certify_and_query.py" "$PROJECT" "$WORK/warehouse"
$JANUS context build --path "$PROJECT" >/dev/null

step "11. Agents queue corrections; a person reviews them"
OUT="$("$PYTHON" "$HERE/corrections_demo.py" "$PROJECT")"
echo "$OUT" | grep -v '^IDS '
IDS="$(echo "$OUT" | sed -n 's/^IDS //p')"
set -- $IDS
$JANUS context review --path "$PROJECT"
$JANUS context review approve "$1" --path "$PROJECT"
$JANUS context review reject "$2" --reason "the schema is the source of truth, not the agent" --path "$PROJECT" || true
$JANUS context build --path "$PROJECT" >/dev/null
$JANUS context validate --path "$PROJECT" | tail -1 || true

step "12. A failing apply is rolled back"
"$PYTHON" "$HERE/failed_apply.py" "$PROJECT"
$JANUS context draft apply dim_store_candidate --path "$PROJECT" || echo "(rejected, as intended)"
test ! -e "$PROJECT/models/dim_store_candidate" && echo "models/ unchanged: no dim_store_candidate"

printf '\nDone. The project is in %s\n' "$PROJECT"

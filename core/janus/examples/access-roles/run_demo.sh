#!/usr/bin/env bash
# Role-based rows and columns, end to end, over the HTTP API.
#
#   ./run_demo.sh                                              # janus on PATH
#   JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh    # from a source checkout
#
# An analyst (customer 1, session_level 1) and a manager (session_level 3) query
# the same orders. Everything is written under ./work/.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
JANUS="${JANUS:-janus}"
PYTHON="${PYTHON:-python3}"
PORT="${PORT:-8765}"
WORK="$HERE/work"
BASE="http://127.0.0.1:$PORT"

step() { printf '\n== %s ==\n' "$1"; }

cd "$HERE"
"$PYTHON" -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$WORK"
mkdir -p "$WORK/home" "$WORK/warehouse"
export JANUS_HOME="$WORK/home"
export JANUS_PROJECT_HOME="$WORK/project"
PROJECT="$WORK/project"

# Tokens are random per run; the config only names the environment variables.
export JANUS_TOKEN_ANALYST="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(24))')"
export JANUS_TOKEN_MANAGER="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(24))')"

step "1. Warehouse (DuckDB: customers, orders)"
"$PYTHON" "$HERE/make_warehouse.py" "$WORK/warehouse/warehouse.duckdb"

step "2. Connection profile and project"
cat > "$JANUS_HOME/profiles.yml" <<YAML
active: demo
profiles:
  demo:
    datasource: duckdb
    url: $WORK/warehouse
    format: duckdb
YAML
$JANUS context init --path "$PROJECT" --empty >/dev/null
"$PYTHON" - "$PROJECT/janus_project.yml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(
    re.sub(r"(?m)^data_source:.*$", "data_source: duckdb", text)
)
PY

step "3. Models from the database, then the access rules"
$JANUS context draft --from-db --path "$PROJECT" >/dev/null
for model in customers orders; do
  $JANUS context draft apply "$model" --path "$PROJECT" >/dev/null
done
"$PYTHON" "$HERE/add_rules.py" "$PROJECT/models/orders/metadata.yml"
$JANUS context build --path "$PROJECT"

step "4. Check the access config against the model"
$JANUS access report --path "$PROJECT" --access-config "$HERE/janus_access.yml"

step "5. Start the HTTP API with the access config"
$JANUS serve api --project "$PROJECT" --port "$PORT" \
  --access-config "$HERE/janus_access.yml" >"$WORK/api.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do
  curl -s "$BASE/health" >/dev/null 2>&1 && break
  sleep 0.5
done
echo "server up at $BASE"

call() {  # call <label> <token-or-none> <path> <json>
  local label="$1" token="$2" path="$3" body="$4"
  local args=(-s -w '\n  HTTP %{http_code}\n' -X POST "$BASE$path" -H 'Content-Type: application/json' -d "$body")
  if [ "$token" != none ]; then args+=(-H "Authorization: Bearer $token"); fi
  printf '\n-- %s\n' "$label"
  curl "${args[@]}"
}

SQL_ID='SELECT order_id FROM orders ORDER BY order_id'
SQL_AMOUNT='SELECT order_id, amount FROM orders ORDER BY order_id'

step "6. Calls"
call "no token" none /query "{\"sql\": \"$SQL_ID\"}"
call "analyst: own orders only" "$JANUS_TOKEN_ANALYST" /query "{\"sql\": \"$SQL_ID\"}"
call "analyst: amount is restricted (expect Permission Denied)" "$JANUS_TOKEN_ANALYST" /query "{\"sql\": \"$SQL_AMOUNT\"}"
call "analyst: override session_customer=2 (allowed)" "$JANUS_TOKEN_ANALYST" /query \
  "{\"sql\": \"$SQL_ID\", \"properties\": {\"session_customer\": 2}}"
call "analyst: try to override session_level (refused)" "$JANUS_TOKEN_ANALYST" /query \
  "{\"sql\": \"$SQL_ID\", \"properties\": {\"session_level\": 3}}"
call "analyst: try to choose a role (refused)" "$JANUS_TOKEN_ANALYST" /query \
  "{\"sql\": \"$SQL_ID\", \"role\": \"manager\"}"
call "manager: every order, with amount" "$JANUS_TOKEN_MANAGER" /query "{\"sql\": \"$SQL_AMOUNT\"}"
call "manager: acts as analyst (amount restricted again)" "$JANUS_TOKEN_MANAGER" /query \
  "{\"sql\": \"$SQL_ID\", \"role\": \"analyst\"}"
call "dry-plan for the analyst (filter shown, no data read)" "$JANUS_TOKEN_ANALYST" /dry-plan \
  "{\"sql\": \"$SQL_ID\"}"

step "7. Audit trail (work/access_audit.jsonl)"
"$PYTHON" "$HERE/show_audit.py" "$WORK/access_audit.jsonl"

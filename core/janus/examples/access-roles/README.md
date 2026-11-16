# Access roles demo

One `orders` table, read by two callers who see different rows and columns:
an analyst and a manager. The calls go over the HTTP API. Nothing external is
needed: the warehouse is a DuckDB file that the script creates.

## What it shows

- **Row rules** (`customer_id = @session_customer OR @session_level >= 3`): an
  analyst sees only their own orders; a manager sees all of them.
- **Column rules** (`amount` needs `session_level >= 2`): the analyst gets a
  `Permission Denied` error when asking for `amount`.
- **Server-side roles**: each role's properties come from a one-row SQL query
  on the server. A token decides the role. Callers cannot choose a role unless
  the token allows it.
- **Overrides**: the analyst may override `session_customer` within the allow
  list and nothing else.
- **Audit**: every call is recorded, including refused ones.

## Requirements

- `janus` with the `mcp` extra: `pip install 'janusai[mcp]'`
- DuckDB (a dependency of janus)
- `curl` and `bash`

## Run it

```bash
./run_demo.sh                                            # janus on PATH
JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh  # from a source checkout
```

Options through environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `JANUS` | `janus` | The command that starts janus |
| `PYTHON` | `python3` | The interpreter for the helper scripts |
| `PORT` | `8765` | Port for the HTTP API |

The script exits with status 0 when every step succeeds. The HTTP server is
stopped on exit.

Everything the run writes goes under `./work/` (git-ignored), so it is safe to
delete and re-run.

## What the script does

| Step | What happens |
|---|---|
| 1. Warehouse | `make_warehouse.py` writes `work/warehouse/warehouse.duckdb` with `customers` (4 rows) and `orders` (6 rows). |
| 2. Profile and project | A DuckDB profile in `work/home/profiles.yml`; a project created with `context init` and pointed at DuckDB. |
| 3. Models and rules | `context draft --from-db` generates the models; `draft apply` promotes them; `add_rules.py` adds the rules to `orders`; `context build` compiles `target/mdl.json`. |
| 4. Config check | `janus access report` shows what each role can see, and checks the config against the model. |
| 5. Server | `janus serve api --access-config janus_access.yml` starts on `PORT`. Two random tokens are generated and exported as environment variables. |
| 6. Calls | Nine HTTP calls, each printed with its status code. |
| 7. Audit | `show_audit.py` prints `work/access_audit.jsonl`, one line per call. |

## Files

| File | Purpose |
|---|---|
| `run_demo.sh` | Runs all the steps above. |
| `make_warehouse.py` | Creates the DuckDB warehouse. |
| `add_rules.py` | Adds the row and column rules to the generated `orders` model. |
| `janus_access.yml` | Server-side roles and tokens. Names environment variables; holds no secrets. |
| `show_audit.py` | Prints the audit trail. |

## The configuration

### Access config: `janus_access.yml`

```yaml
version: 1
roles:
  analyst:
    sql: SELECT 1 AS session_level, 1 AS session_customer
    allow_override: [session_customer]
  manager:
    sql: SELECT 3 AS session_level, 0 AS session_customer
    allow_override: []
tokens:
  - id: svc_analyst_app
    token_env: JANUS_TOKEN_ANALYST
    default_role: analyst
    may_request_role: false
    may_override: true
  - id: svc_bi_console
    token_env: JANUS_TOKEN_MANAGER
    default_role: manager
    may_request_role: true
    may_override: false
audit:
  path: work/access_audit.jsonl
  record_sql: true
```

- A role's `sql` returns one row. Its column names are the session properties
  the model rules read.
- `allow_override` lists the properties a caller may change in a request.
- `may_request_role` lets a token pick a role other than its default.
- `may_override` lets a token change any property in the allow list.

### Model rules: `orders` (after `add_rules.py`)

```yaml
- name: amount
  type: DECIMAL(10, 2)
  column_level_access_control:
    name: amount_for_managers
    required_properties:
    - name: session_level
      required: true
    operator: GREATER_THAN_OR_EQUALS
    threshold: '2'
row_level_access_controls:
- name: own_or_manager
  required_properties:
  - name: session_customer
    required: true
  - name: session_level
    required: true
  condition: customer_id = @session_customer OR @session_level >= 3
```

Every property a rule uses must be `required: true`. An optional property would
make the rule disappear silently, so the config check refuses it.

### Profile and project

`work/home/profiles.yml` points the connection at the warehouse directory:

```yaml
active: demo
profiles:
  demo:
    datasource: duckdb
    url: <path to work/warehouse>
    format: duckdb
```

`work/project/janus_project.yml` declares `data_source: duckdb`.

## Expected output

The analyst's row filter, as the config check reports it:

```
role analyst  model orders
    rows: own_or_manager: customer_id = @session_customer OR @session_level >= 3
    denied: amount (session_level=1 fails GREATER_THAN_OR_EQUALS 2)
role manager  model orders
    rows: own_or_manager: customer_id = @session_customer OR @session_level >= 3
    columns: amount
ok: no errors or warnings
```

The calls, with their status codes:

| Call | Status | Result |
|---|---|---|
| no token | 401 | `missing or invalid bearer token` |
| analyst: `SELECT order_id FROM orders` | 200 | orders 101, 102 (customer 1) |
| analyst: selects `amount` | 422 | `Permission Denied` on `amount` |
| analyst: `session_customer=2` | 200 | orders 103, 106 (customer 2) |
| analyst: overrides `session_level` | 403 | `override_not_allowed` |
| analyst: `role: manager` | 403 | `role_not_allowed` |
| manager: every order, with `amount` | 200 | all six orders |
| manager: `role: analyst` | 200 | orders 101, 102; `amount` restricted |
| analyst: dry-plan | 200 | SQL contains `customer_id = 1 OR 1 >= 3` |

The audit trail, one line per call:

```
ok     token=svc_analyst_app role=analyst sql='SELECT order_id FROM orders ...'
error  token=svc_analyst_app role=analyst sql='SELECT order_id, amount FROM orders ...'
ok     token=svc_analyst_app role=analyst sql='SELECT order_id FROM orders ...'
denied token=svc_analyst_app code=override_not_allowed sql='...'
denied token=svc_analyst_app code=role_not_allowed sql='...'
ok     token=svc_bi_console role=manager sql='SELECT order_id, amount FROM orders ...'
ok     token=svc_bi_console role=analyst sql='SELECT order_id FROM orders ...'
```

## Make your own call

Start the server yourself, with the same config:

```bash
janus serve api --project work/project --port 8765 --access-config janus_access.yml
```

Export a token that matches one of the configured environment variables, then call it:

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_ANALYST" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id FROM orders"}'
```

With `properties`, the same call can override an allowed property:

```json
{"sql": "SELECT order_id FROM orders", "properties": {"session_customer": 2}}
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `error: access config: ... environment variable ... is empty or unset` | The token variable named in `token_env` is not set in this shell. |
| `Error: no target/mdl.json` | `context build` did not run, or ran for a different project. |
| `Connection refused` on the calls | The server is not up yet. The script waits up to 30 seconds; a manual start needs a moment. |
| `profile 'demo' not found` | `JANUS_HOME` is not pointing at `work/home`. Run through `run_demo.sh`. |
| Exit status 1 from `access report` | The config has an error. The report lists it; fix it before the server starts. |

The server log is in `work/api.log`.

## What this demo does not cover

- MCP over HTTP and over stdio. The MCP tools accept the same `role` and
  `properties`, and the HTTP token path is tested in
  `tests/unit/test_access_mcp_http.py`, but the demo does not run them.
- A real database. The warehouse is DuckDB.
- Certified models. The warnings about "not certified" are expected here.

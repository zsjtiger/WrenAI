# Access roles demo

The same `orders` table, read by two callers with different rows and columns,
over the HTTP API. Nothing external is needed: the warehouse is a DuckDB file.

## Run

```bash
./run_demo.sh                                            # janus on PATH
JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh  # from a source checkout
```

Needs `janus` with the `mcp` extra (`pip install 'janusai[mcp]'`) and DuckDB.
Everything is written under `./work/`, which is git-ignored.

## What is in here

| File | Role |
|---|---|
| `make_warehouse.py` | Builds the DuckDB warehouse: `customers` and `orders`. |
| `add_rules.py` | Adds the data team's access rules to the `orders` model. |
| `janus_access.yml` | Server-side roles and tokens. It names environment variables; it holds no secrets. |
| `show_audit.py` | Prints the audit trail. |
| `run_demo.sh` | Runs everything: warehouse, models, rules, `janus access report`, the API, and the calls. |

## The rules

- **Row rule** on `orders`: a row is visible when `customer_id = @session_customer`,
  or when `@session_level >= 3`. Both properties are required.
- **Column rule** on `orders.amount`: visible only when `@session_level >= 2`.

## The roles

| Role | `session_level` | `session_customer` | Can override | Can choose a role |
|---|---|---|---|---|
| `analyst` (token `svc_analyst_app`) | 1 | 1 | `session_customer` | no |
| `manager` (token `svc_bi_console`) | 3 | 0 | nothing | yes |

## Expected results

| Call | Result |
|---|---|
| no token | 401 |
| analyst: `SELECT order_id FROM orders` | orders 101, 102 (customer 1) |
| analyst: selects `amount` | 422, `Permission Denied` |
| analyst: `session_customer=2` | orders 103, 106 (customer 2) |
| analyst: overrides `session_level` | 403, `override_not_allowed` |
| analyst: chooses `role: manager` | 403, `role_not_allowed` |
| manager: every order, with `amount` | all six orders |
| manager: `role: analyst` | orders 101, 102 |
| dry-plan for the analyst | `WHERE customer_id = 1 OR 1 >= 3` |

Every call is written to `work/access_audit.jsonl`, including the refused ones.

## Calling it yourself

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_ANALYST" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id FROM orders"}'
```

Start the server with `janus serve api --project <project> --access-config janus_access.yml`.
The token comes from the environment variable the config names.

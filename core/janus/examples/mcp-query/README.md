# MCP query demo

Query a database through the janus MCP server, with no external database.
A DuckDB file is the warehouse. The demo generates the models from it, starts
`janus serve mcp` over stdio, and calls `run_sql` the way an agent would.

## Run

```bash
./run_demo.sh                                            # janus on PATH
JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh  # from a source checkout
```

Needs the `mcp` extra (`pip install 'janusai[mcp]'`) and DuckDB. Everything is
written under `./work/`, which is git-ignored.

## What it does

1. `make_warehouse.py` writes `work/warehouse/warehouse.duckdb` with two tables:
   `customers` (4 rows) and `orders` (6 rows).
2. The profile in `work/home/profiles.yml` points janus at that file.
3. `janus context draft --from-db` generates the models; `draft apply` promotes
   them. Then `janus context build` compiles `target/mdl.json`.
4. `mcp_client.py` starts `janus serve mcp --project work/project` over stdio,
   lists the tools, and runs two queries with `run_sql`. The second query joins
   `orders` to `customers`.

## Expected output (excerpt)

```
> SELECT customer_id, name, region FROM customers ORDER BY customer_id
    {'customer_id': 1, 'name': 'Ada', 'region': 'APAC'}
    ...
    models used: ['customers']

> SELECT o.order_id, c.name, o.amount, o.status FROM orders o JOIN ...
    {'order_id': 101, 'name': 'Ada', 'amount': 120.0, 'status': 'shipped'}
    ...
    models used: ['customers', 'orders']
```

## Calling it from your own client

Register the server as a stdio command and send `run_sql` with only the SQL:

```bash
claude mcp add janus -- janus serve mcp --project /path/to/project
```

```json
{"name": "run_sql",
 "arguments": {"sql": "SELECT order_id, amount FROM orders LIMIT 10"}}
```

No access rules are configured here. A model with a `required: true` session
property would fail unless the property is supplied; that case is out of scope
for this demo.

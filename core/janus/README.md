# janusai

🌐 **English** · [简体中文](./README.zh-CN.md)

[![PyPI version](https://img.shields.io/pypi/v/janusai.svg)](https://pypi.org/project/janusai/)
[![Python](https://img.shields.io/pypi/pyversions/janusai.svg)](https://pypi.org/project/janusai/)
[![License](https://img.shields.io/pypi/l/janusai.svg)](https://github.com/CrossNow/JanusAI/blob/main/LICENSE)

Janus AI CLI and Python SDK — semantic SQL layer for 20+ data sources.

Translate natural SQL queries through an [MDL (Modeling Definition Language)](https://docs.crossnow.cn/) semantic layer and execute them against your database. Powered by [Apache DataFusion](https://datafusion.apache.org/).

## Installation

```bash
pip install janusai                 # Core (DuckDB included)
pip install 'janusai[postgres]'     # PostgreSQL
pip install 'janusai[mysql]'        # MySQL
pip install 'janusai[bigquery]'     # BigQuery
pip install 'janusai[snowflake]'    # Snowflake
pip install 'janusai[clickhouse]'   # ClickHouse
pip install 'janusai[trino]'        # Trino
pip install 'janusai[mssql]'        # SQL Server
pip install 'janusai[databricks]'   # Databricks
pip install 'janusai[redshift]'     # Redshift
pip install 'janusai[spark]'        # Spark
pip install 'janusai[athena]'       # Athena
pip install 'janusai[oracle]'       # Oracle
pip install 'janusai[memory]'       # Schema & query memory (LanceDB)
pip install 'janusai[memory-onnx]'  # Same, torch-free (onnxruntime instead of PyTorch)
pip install 'janusai[ui]'           # Browser-based profile form (starlette + uvicorn)
pip install 'janusai[main]'         # memory + interactive prompts + ui
pip install 'janusai[all]'          # All connectors + main
```

Requires Python 3.11+.

## Quick start

**1. Initialize a project** — scaffolds a YAML-based MDL project:

```bash
mkdir my-project && cd my-project
janus context init
```

This creates `janus_project.yml`, `models/`, and `views/`. Edit `janus_project.yml` to set your `data_source` and add models under `models/`:

```yaml
# janus_project.yml
schema_version: 2
name: my_project
catalog: janus
schema: public
data_source: postgres
```

```yaml
# models/orders/metadata.yml
name: orders
table_reference:
  schema: mydb
  table: orders
columns:
  - name: order_id
    type: integer
  - name: customer_id
    type: integer
  - name: total
    type: double
  - name: status
    type: varchar
primary_key: order_id
```

> **Already have an MDL JSON?** Import it directly:
> `janus context init --from-mdl path/to/mdl.json`

**2. Configure a connection profile:**

```bash
# Browser form (recommended, requires janusai[ui])
janus profile add my-db --ui

# Interactive terminal prompts
janus profile add my-db --interactive

# Import from an existing connection file
janus profile add my-db --from-file connection_info.json
```

**3. Build the manifest:**

```bash
janus context build
```

This compiles YAML files into `target/mdl.json`. The CLI auto-discovers this file when you run queries from within the project directory.

**4. Run queries:**

```bash
janus --sql 'SELECT order_id FROM "orders" LIMIT 10'
```

`janus` walks up from the current directory to find `janus_project.yml` and uses `target/mdl.json`. You can also pass `--mdl path/to/mdl.json` explicitly.

For the full CLI reference and per-datasource connection field reference, see [`docs/cli.md`](docs/cli.md) and [`docs/connections.md`](docs/connections.md).

**4a. (Optional) Aggregation queries with cubes** — define cubes under `cubes/`,
then query them with a structured input instead of writing `GROUP BY` SQL by hand:

```bash
janus cube list
janus cube describe revenue
janus cube query --cube revenue --measures total --time-dimension "order_date:month"
```

The translator produces `DATE_TRUNC` / `GROUP BY` / `WHERE` clauses for you and
runs them through the same engine path as `janus --sql`. See the
[Cube guide](../../docs/core/guides/cubes.md) for full YAML structure
and the [CLI reference](../../docs/core/reference/cli.md#janus-cube--pre-aggregation-queries) for all
flags.

**5. (Optional) Configure security policy** — create `~/.janus/config.json`:

```json
{
  "strict_mode": true,
  "denied_functions": ["pg_read_file", "dblink", "lo_import"]
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `strict_mode` | `false` | When `true`, every table in a query must be defined in the MDL. Queries referencing undeclared tables are rejected before execution. |
| `denied_functions` | `[]` | List of function names (case-insensitive) that are forbidden in queries. |

**6. (Optional) Index schema for semantic search** (requires `janusai[memory]`,
or `janusai[memory-onnx]` for a torch-free install):

```bash
janus memory index                              # index MDL schema
janus memory fetch -q "customer order price"    # fetch relevant schema context
janus memory store --nl "top customers" --sql "SELECT ..."  # store NL→SQL pair
janus memory recall -q "best customers"         # retrieve similar past queries
janus memory watch                              # auto-reindex on schema/query changes
```

`memory-onnx` runs the same weights through onnxruntime instead of PyTorch, so
it produces the same vectors and existing indexes stay valid -- it is a much
smaller install, not a different index. When both extras are present, onnx is
used; set `JANUS_EMBEDDING_BACKEND=sentence-transformers` to override, and
`janus memory status` reports which one is live.

**7. (Optional) Build a shareable CReport app** — turn the context layer into a
browser-side dashboard (powered by `janus-core-wasm`) and deploy it to Vercel or
Cloudflare Pages. The CLI owns the build instruction + deterministic state; an
agent authors the app from it:

```bash
janus creport build sales --prompt "orders dashboard" --data-mode snapshot  # print build instruction
# agent authors apps/sales/ from the instruction (mdl.json + data/*.parquet)
janus creport register sales --data-mode snapshot   # record the app
janus creport verify sales                          # preflight (files, MDL, data, secret scan)
janus creport open sales                            # local preview
janus creport deploy sales --provider vercel        # ship a shareable URL (preview; --prod for production)
```

Tokens come from the env / `.env` (`VERCEL_TOKEN` / `CLOUDFLARE_API_TOKEN`),
never CLI flags; Cloudflare needs `wrangler` installed. See the
[CReport guide](../../docs/core/guides/creport.md) and the
[CLI reference](../../docs/core/reference/cli.md#janus-creport--build--deploy-creport-apps).

**8. (Optional) Serve an MCP server** — expose the project's query, schema, and
knowledge tools to Claude Desktop/Code, Cursor, or any MCP client. Runs
in-process against the compiled MDL — no separate service:

```bash
janus serve mcp                                # stdio (default) — client spawns this as a child process
janus serve mcp --transport http --port 8080   # local Streamable HTTP for other clients
```

Requires `janus context build` to have already run and the `mcp` extra:
`pip install 'janusai[mcp]'`. See the
[MCP guide](../../docs/core/guides/mcp.md) and the
[CLI reference](../../docs/core/reference/cli.md#janus-serve--mcp-server) for
the full tool/resource list and client wiring.

---

## Connection profiles

Profiles let you store named connection configurations in `~/.janus/profiles.yml` and switch between them easily — useful when working across multiple databases or environments.

```bash
# Add a profile (browser form, interactive prompts, or file import)
janus profile add prod --ui                        # opens http://localhost:<port>
janus profile add staging --interactive            # terminal prompts
janus profile add local --from-file conn.json      # import existing file

# List and switch profiles
janus profile list                                 # * marks the active profile
janus profile switch prod

# Inspect a profile (sensitive fields masked)
janus profile debug prod

# Remove a profile
janus profile rm old-profile --force
```

The `--ui` flag opens a browser-based form that auto-derives fields from each datasource's schema — including file upload for BigQuery credentials, variant selection for Databricks/Redshift, and sensible defaults for all 20+ supported sources. Requires `pip install 'janusai[ui]'`.

Once a profile is active, `janus` uses it automatically:

```bash
janus profile switch prod
janus --sql 'SELECT COUNT(*) FROM "orders"'        # connects using prod profile
```

---

## Python SDK

```python
import base64, orjson
from janus import JanusEngine, DataSource

manifest = { ... }  # your MDL dict
manifest_str = base64.b64encode(orjson.dumps(manifest)).decode()

with JanusEngine(manifest_str, DataSource.mysql, {"host": "...", ...}) as engine:
    result = engine.query('SELECT * FROM "orders" LIMIT 10')
    print(result.to_pandas())
```

---

## Development

Prerequisites: `just` and `uv`. (Rust + Cargo are only needed for the
local-engine recipes below.)

### Standard setup (no Rust toolchain)

```bash
just install        # uv sync — pulls the prebuilt janus-core-py wheel from PyPI
just lint           # Ruff format check + lint
just format         # Auto-fix
```

`just install` is a plain `uv sync`: it installs the locked prebuilt `janus-core-py` engine binding and the development tools from uv's default `dev` dependency group. No compilation required. This is enough for all Python-side development. Use `just install-extra <extra>` or `just install-all` for data-source extras.

### Engine development (changing the Rust core)

Only needed when you modify `../janus-core-py` (or `../janus-core`) and want
`core/janus` to run against your local build. Requires Rust + Cargo.

```bash
just install-local    # uv sync + build the local wheel + overlay it into .venv
just use-local-core   # rebuild + re-overlay after each subsequent Rust change
```

The run recipes (`just test*`, `just lint`, `just dev`) use `uv run --no-sync`,
so they never revert a locally overlaid engine back to the lockfile version. If
dependencies change, re-run an install recipe first.

| Command | What it runs | Docker needed |
|---------|-------------|---------------|
| `just test-unit` | Unit tests (engine, CTE rewriter, field registry, profiles) | No |
| `just test-duckdb` | DuckDB connector tests | No |
| `just test-postgres` | PostgreSQL connector tests | Yes |
| `just test-mysql` | MySQL connector tests | Yes |
| `just test` | All tests | Yes |

Profile web tests (`test_profile_web.py`) require `janusai[ui]`:

```bash
uv sync --extra ui
uv run --no-sync pytest tests/test_profile_web.py -v
```

## Publishing

```bash
./scripts/publish.sh            # Build + publish to PyPI
./scripts/publish.sh --test     # Build + publish to TestPyPI
./scripts/publish.sh --build    # Build only
```

## License

Apache-2.0

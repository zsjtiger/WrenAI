---
name: usage
description: "Janus Engine CLI workflow guide for AI agents. Answer data questions end-to-end using the janus CLI: gather schema context, recall past queries, write SQL through the MDL semantic layer, execute, and learn from confirmed results. Use when: user asks a data question, requests a report or analysis, asks about metrics, revenue, customers, orders, trends, or any business data; user says 'how many', 'show me', 'what is the', 'top N', 'compare', 'trend', 'growth', 'breakdown'; user wants to explore, analyze, filter, aggregate, or summarize data from a database; agent needs to query data, connect a data source, handle errors, or manage MDL changes via the janus CLI."
license: Apache-2.0
metadata:
  author: janusai
---

# Janus Engine CLI — Agent Workflow Guide

> This guide is served by the `janus` CLI (`janus skills get usage`), so it always matches your installed janusai version. Pull the deeper reference docs with `janus skills get usage --full`.

## Preflight — Verify environment and installation

**Goal:** Ensure the `janus` CLI is available before entering any workflow.

### Step 1 — Check Python virtual environment

Run `python -c "import sys; print(sys.prefix)"` (or equivalent) to determine
whether a virtual environment is active.

- If **no venv is active**, warn the user and ask whether to:
  - Create one (e.g., `python -m venv .venv && source .venv/bin/activate`)
  - Continue without a venv (not recommended — may pollute global packages)

### Step 2 — Check if the `janus` CLI is installed

Run `janus --version`. If the command is not found or errors:

1. Tell the user that the `janus` CLI is not installed.
2. Ask if you should help install it.
3. If the user agrees, determine the **datasource extra** to install:

   **Auto-detect from project:** Check whether the current directory is inside
   a janus project (look for `janus_project.yml` up to the repository root).
   If found, read the active profile with `cat ~/.janus/profiles.yml` or look
   for a datasource hint in the project's profile configuration. Extract the
   datasource type from there.

   **Ask the user:** If no project is detected or no datasource can be
   inferred, ask the user which database they plan to connect to. Valid
   extras: `postgres` (for Aurora Postgres), `mysql` (for Aurora MySQL), `bigquery`, `snowflake`, `clickhouse`,
   `trino`, `mssql`, `databricks`, `redshift`, `spark`, `athena`, `oracle`.
   DuckDB is included by default — no extra needed.

4. Install with the detected or chosen extra:
   ```bash
   # DuckDB (no extra needed)
   pip install "janusai"

   # Other datasources
   pip install "janusai[<datasource>]"
   ```
   To also enable semantic memory, interactive prompts, and web UI (recommended):
   ```bash
   pip install "janusai[<datasource>,main]"
   # or for DuckDB:
   pip install "janusai[main]"
   ```

5. Verify: `janus --version`

If `janus --version` succeeds, proceed to the relevant workflow below.

---

The `janus` CLI queries databases through an MDL (Model Definition Language) semantic layer. You write SQL against model names, not raw tables. The engine translates to the target dialect.

Two things drive everything:
- **Profile** — database connection + datasource type, managed via `janus profile` (stored in `~/.janus/profiles.yml`)
- **Project** — MDL model definitions in YAML, compiled to `target/mdl.json` via `janus context build`

The CLI reads the active profile for connection info and datasource. Use `janus profile list` to see which profile is active, `janus profile switch <name>` to change it. `dry-plan` also accepts `--datasource` / `-d` for transpile-only use without a profile.

For memory-specific decisions, see the `memory` reference (run `janus skills get usage --full`).
For SQL syntax, CTE-based modeling, and error diagnosis, see the `janus-sql` reference (run `janus skills get usage --full`).
For project structure, MDL field definitions, and CLI workflow details, see the [documentation](https://github.com/CrossNow/JanusAI/tree/main/docs/core).

---

## Workflow 1: Answering a data question

### Step 1 — Gather context

| Situation | Command |
|-----------|---------|
| Default | `janus memory fetch -q "<question>"` |
| Need specific model's columns | `janus memory fetch -q "..." --model <name> --threshold 0` |
| Memory not installed | Read `target/mdl.json` in the project directory, or run `janus context show` |

If this is the first query in the conversation, also run:

```text
janus context instructions
```

If it returns content, treat it as **rules that override defaults** — apply them to all subsequent queries in this session.

### Step 2 — Recall past queries

```bash
janus memory recall -q "<question>" --limit 3
```

Use results as few-shot examples. Skip if empty.

### Step 2.5 — Assess complexity (before writing SQL)

If the question involves **any** of the following, consider decomposing:
- Multiple metrics or aggregations (e.g., "churn rate AND expansion revenue")
- Multi-step calculations (e.g., "month-over-month growth rate")
- Comparisons across segments (e.g., "by plan tier, by region")
- Time-series analysis requiring baseline + change (e.g., "retention curve")

**Decomposition strategy:**
1. Identify the sub-questions (e.g., "total subscribers at start" + "subscribers who cancelled" → churn rate)
2. For each sub-question:
   - `janus memory recall -q "<sub-question>"` — check if a similar pattern exists
   - Write and execute a simple SQL
   - Note the result
3. Combine sub-results to answer the original question

**When NOT to decompose:**
- Single-table aggregation with GROUP BY — just write the SQL
- Simple JOINs that the MDL relationships already define
- Questions where `memory recall` returns a near-exact match

This is a judgment call, not a rigid rule. If you're confident in a single
query, go ahead. Decompose when the SQL would be hard to debug if it fails.

### Step 3 — Write, verify, and execute SQL

**For simple queries** (single table or simple MDL-defined JOINs, straightforward aggregation):
Execute directly:
```bash
janus --sql 'SELECT c_name, SUM(o_totalprice) FROM orders
JOIN customer ON orders.o_custkey = customer.c_custkey
GROUP BY 1 ORDER BY 2 DESC LIMIT 5'
```

**For complex queries** (non-trivial JOINs not covered by MDL relationships, subqueries, multi-step logic):
Verify first with dry-plan:
```bash
janus dry-plan --sql 'SELECT ...'
```

Check the expanded SQL output:
- Are the correct models and columns referenced?
- Do the JOINs match expected relationships?
- Are CTEs expanded correctly?

If the expanded SQL looks wrong, fix before executing.
If it looks correct, proceed:
```bash
janus --sql 'SELECT ...'
```

**SQL rules:**
- Target MDL model names, not database tables
- Write dialect-neutral SQL — the engine translates

### Step 4 — Store and continue

After successful execution, **store the query by default**:

```bash
janus memory store --nl "<user's original question>" --sql "<the SQL>"
```

**Skip storing only when:**
- The query failed or returned an error
- The user said the result is wrong
- The query is exploratory (`SELECT * ... LIMIT N` without analytical clauses)
- There is no natural language question — just raw SQL
- The user explicitly asked not to store

The CLI auto-detects exploratory queries — if you see no store hint
after execution, the query was classified as exploratory.

| Outcome | Action |
|---------|--------|
| User confirms correct | Store |
| User continues with follow-up | Store, then handle follow-up |
| User says nothing (but question had clear NL description) | Store |
| User says wrong | Do NOT store — fix the SQL |
| Query error | See Error recovery below |

---

## Workflow 2: Error recovery

### "table not found"

1. Verify model name: `janus memory fetch -q "<name>" --type model --threshold 0`
2. Check MDL exists: `ls target/mdl.json` (or `janus context show`)
3. Verify column: `janus memory fetch -q "<column>" --model <name> --threshold 0`

### Connection error

1. Check active profile: `janus profile debug`
2. Verify datasource and connection fields are correct
3. Test: `janus --sql "SELECT 1"`
4. Valid datasource values: `postgres` (for Aurora Postgres), `mysql` (for Aurora MySQL), `bigquery`, `snowflake`, `clickhouse`, `trino`, `mssql`, `databricks`, `redshift`, `spark`, `athena`, `oracle`, `duckdb`
5. If no profile exists, create one: `janus profile add --ui` (or `--interactive` / `--from-file`)

### SQL syntax / planning error (enhanced)

#### Layer 1: Identify the failure point

```bash
janus dry-plan --sql "<failed SQL>"
```

| dry-plan result | Failure layer | Next step |
|-----------------|---------------|-----------|
| dry-plan fails | MDL / semantic | → Layer 2A |
| dry-plan succeeds, execution fails | DB / dialect | → Layer 2B |

#### Layer 2A: MDL-level diagnosis (dry-plan failed)

The dry-plan error message tells you exactly what's wrong:

| Error pattern | Diagnosis | Fix |
|---------------|-----------|-----|
| `column 'X' not found in model 'Y'` | Wrong column name | `janus memory fetch -q "X" --model Y --threshold 0` to find correct name |
| `model 'X' not found` | Wrong model name | `janus memory fetch -q "X" --type model --threshold 0` |
| `ambiguous column 'X'` | Column exists in multiple models | Qualify with model name: `ModelName.column` |
| Planning error with JOIN | Relationship not defined in MDL | Check available relationships in context |

**Key principle**: Fix ONE issue at a time. Re-run dry-plan after each fix
to see if new errors surface.

#### Layer 2B: DB-level diagnosis (dry-plan OK, execution failed)

The DB error + dry-plan output together pinpoint the issue:

1. Read the dry-plan expanded SQL — this is what actually runs on the DB
2. Compare with the DB error message:

| Error pattern | Diagnosis | Fix |
|---------------|-----------|-----|
| Type mismatch | Column type differs from assumed | Check column type in context, add explicit CAST |
| Function not supported | Dialect-specific function | Use dialect-neutral alternative |
| Permission denied | Table/schema access | Check connection credentials |
| Timeout | Query too expensive | Simplify: reduce JOINs, add filters, LIMIT |

**For small models**: If the error message is unclear, try simplifying
the query to the smallest failing fragment. Execute subqueries independently
to isolate which part fails.

For the CTE rewrite pipeline and additional error patterns, see the `janus-sql` reference (run `janus skills get usage --full`).

---

## Workflow 3: Connecting a new data source

1. Add a profile: `janus profile add --ui` (or `--interactive` / `--from-file`)
2. Test connection: `janus profile debug`
3. Test query: `janus --sql "SELECT 1"`
4. Initialize project: `janus context init`
5. Build manifest: `janus context build`
6. Index: `janus memory index`
7. Verify: `janus --sql "SELECT * FROM <model> LIMIT 5"`

---

## Workflow 4: After MDL changes

When model YAML files are updated, rebuild and re-index:

```bash
# 1. Validate changes
janus context validate

# 2. Rebuild manifest
janus context build

# 3. Re-index schema memory
janus memory index

# 4. Verify
janus --sql "SELECT * FROM <changed_model> LIMIT 1"
```

---

## Command decision tree

```text
Get data back           → janus --sql "..."
Aggregation across dims → janus cube query --cube <name> --measures <m> (if cube defined)
Ranked / top-N          → janus cube query ... --order-by "<measure>:desc" --limit N
See translated SQL only → janus dry-plan --sql "..." (accepts -d <datasource> if no active profile)
Validate against DB     → janus dry-run --sql "..."
Schema context          → janus memory fetch -q "..."
Filter by type/model    → janus memory fetch -q "..." --type T --model M --threshold 0
Store confirmed query   → janus memory store --nl "..." --sql "..."
Few-shot examples       → janus memory recall -q "..."
Index stats             → janus memory status
Re-index after MDL change → janus memory index
Show project context    → janus context show
Rebuild manifest        → janus context build
Check profile           → janus profile debug
Switch profile          → janus profile switch <name>
```

---

## Cube Query Workflow

When the user asks an aggregation question (e.g., "total revenue by month",
"top customers"), check if the MDL defines cubes before writing raw SQL.

### Step 1: Discover cubes

```bash
janus cube list
```

If cubes exist and cover the user's question, prefer cube query over raw SQL.
Lower error rate, especially for small / local models — agents don't have to
hand-write GROUP BY / DATE_TRUNC.

### Step 2: Inspect cube structure

```bash
janus cube describe <cube_name>
```

Shows the cube's baseObject, measures (with expressions), dimensions,
time dimensions, and hierarchies.

### Step 3: Match user's question to cube measures + dimensions

| User phrase | Maps to |
|---|---|
| "total revenue" | `--measures total` |
| "by month" | `--time-dimension "order_date:month"` |
| "in 2024" | `--time-dimension "order_date:month:2024-01-01,2025-01-01"` |
| "for completed orders" | `--filter "status:eq:completed"` |
| "top N customers" | `--dimensions customer --order-by "total:desc" --limit N` |
| "worst / lowest / bottom N" | `--order-by "<measure>:asc" --limit N` |
| "sorted by name" | `--order-by "<dimension>:asc"` |

### Step 4: Execute via CLI flags OR JSON input

CLI flags:

```bash
janus cube query \
  --cube revenue \
  --measures total,order_count \
  --time-dimension "order_date:month:2024-01-01,2025-01-01" \
  --filter "status:eq:completed" \
  --order-by "total:desc" \
  --limit 100
```

**`--limit` without `--order-by` is not a top-N.** It returns an arbitrary N rows
(or the earliest N by the time dimension when one is present). Whenever the user
asks for "top", "best", "worst", or "largest", add `--order-by`.

Ordering rules: the member must be one this query already selects (a measure,
dimension, or time dimension); direction is lowercase `asc` or `desc`; each member
may appear once. Omitting `--order-by` keeps the previous default ordering.

Name the member as the cube declares it. A time dimension appears in the generated
SQL as `<name>__<granularity>`, but `--order-by` wants the declared name:
`--time-dimension "order_date:month" --order-by "order_date:desc"`.

JSON input (good for agent-generated structured queries):

```bash
echo '{"cube":"revenue","measures":["total"]}' | janus cube query --from -
```

Add `--sql-only` to print the generated SQL without executing — useful for
verification before paying for execution on a remote warehouse.

### Step 5: Error recovery

| Error | Action |
|---|---|
| `Unknown measure 'X'` | `janus cube describe <cube>` for available measures |
| `Unknown dimension 'X'` | `janus cube describe <cube>` for available dimensions |
| `Cube 'X' not found` | `janus cube list` |
| `Cannot order by member 'X': member is not selected by the query` | Add `X` to `--measures` / `--dimensions`, or order by a member already selected |
| `Cannot order by member 'X' more than once` | Drop the duplicate — each member may appear once in `--order-by` |
| `` unknown variant `DESC`, expected `asc` or `desc` `` | Directions are lowercase: use `desc`, not `DESC` |
| `Circular dependency detected` | Derived measure references itself — inspect the cube YAML |

### When NOT to use cube query

Fall back to `janus --sql` when:

- Custom JOINs across multiple models
- Window functions, CTEs, or subqueries
- Queries with no aggregation
- No cubes defined in the MDL

---

## Aggregation decision tree

```text
User question → Is it an aggregation question?
                (SUM, COUNT, AVG, GROUP BY, "by month", "per customer", ...)
  ├── Yes → Are cubes defined? (`janus cube list` once at start of session)
  │         ├── Yes → Does a cube cover the question? (`janus cube describe`)
  │         │         ├── Yes → Use `janus cube query` (preferred — lower error rate)
  │         │         └── No  → Write raw SQL with `janus --sql`
  │         └── No  → Write raw SQL with `janus --sql`
  └── No  → Write raw SQL with `janus --sql` (look for memory recall first)
```

---

## Things to avoid

- Do not guess model or column names — check context first
- Do not store failed queries or queries the user said are wrong
- Do not skip storing successful queries with a clear NL question — default is to store
- Do not re-index before every query — once per MDL change
- Do not pass passwords via `--connection-info` if shell history is shared — use profiles (`janus profile add`) or `--connection-file`

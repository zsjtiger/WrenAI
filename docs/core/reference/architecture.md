# Architecture

Janus AI is built as an open context layer for agents. Architecturally, that means two things:

1. Business meaning is stored in explicit project artifacts: MDL, instructions, profiles, and memory.
2. Correctness is handled as a system of primitives the agent can orchestrate, not as one hidden feature.

The result is a stack where agents can generate governed BI, from a SQL answer to a deployed CReport dashboard, through governed business context, while Janus AI handles modeling, planning, validation, execution, and recall.

## Correctness is a system

Text-to-SQL does not become reliable because one metadata field is present or one prompt is clever. It becomes reliable when several pieces work together.

| Pillar | What it means | Where it lives in Janus AI |
| --- | --- | --- |
| **Schema linking** | Knowing which models, columns, and relationships matter for a question. | MDL + memory retrieval (`janus memory fetch`); drift check against the database (`janus context diff`) |
| **Value profiling** | Knowing what values actually appear in the data, such as what `status = 4` means. | Connector behavior, profiling workflows, instructions indexed into memory |
| **Ambiguity detection** | Knowing when the question is underspecified and needs clarification. | Skill orchestration by the agent |
| **Certified definitions** | Knowing which definitions a person has signed off on, and refusing the rest when the project requires it. | `properties.certified` on models; `require_certified` in `~/.janus/config.json` |
| **Generation trace** | Showing how an answer was constructed: models, joins, CTEs, and expanded SQL. | `janus dry-plan`; query results include `provenance` (models used, their certification, knowledge files) |
| **Retry and repair** | Recovering when generated SQL fails or points at the wrong modeled object. | Structured errors, `janus dry-run`, agent retry workflows |
| **Governed change** | Turning a wrong answer into a reviewed fix instead of a silent edit. | `propose_correction` (MCP, with `--allow-write`), `janus context review` |
| **Eval** | Detecting regressions when schemas, definitions, or prompts change. | Golden NL-SQL eval workflows in development |

Janus AI exposes these as primitives. The agent chooses when to fetch, recall, dry-plan, execute, repair, or ask a clarification. The trace stays visible where the agent's reasoning happens.

## System overview

At a high level, Janus AI has four layers:

| Layer | Responsibility |
| --- | --- |
| **Agent workflow** | Skills guide the agent through onboarding, MDL generation, querying, validation, and memory updates. |
| **Project context** | MDL, instructions, profiles, and memory describe what the data means and how it should be used. |
| **Planning engine** | Janus AI expands modeled SQL into executable SQL using the semantic engine and SQL planner. |
| **Execution layer** | Connectors run the planned SQL against the target data source and return results. |

```mermaid
flowchart TD
  user["User / Agent"] --> skills["Agent skills<br/>onboarding · generate MDL · usage"]
  skills --> cli["Janus CLI / Python SDK"]
  skills --> api["MCP server / HTTP API"]
  api --> cli

  cli --> project["Project context<br/>MDL · certification · knowledge"]
  cli --> runtime["Runtime context<br/>profile · memory · history"]

  project --> orchestrator["Plan + execute pipeline"]
  runtime --> orchestrator

  orchestrator --> planner["SQL planner<br/>sqlglot · CTE rewrite · policy"]
  planner --> core["janus-core<br/>Rust semantic engine"]
  core --> connectors["Connectors<br/>20 data sources"]
  connectors --> data["Data source"]

  cli -->|"context diff · draft --from-db"| data
  agent["Agent"] -->|"propose_correction"| review["janus context review<br/>a person approves"]
  review -->|"merge into models/"| project
  runtime -.->|"optional: embedding API · --suggest-terms"| models["Model API<br/>OpenAI-compatible"]
```

The same architecture can also be read as a query path:

```mermaid
sequenceDiagram
  participant U as User / Agent
  participant S as Skill
  participant M as Memory
  participant W as Janus CLI / SDK
  participant P as SQL planner
  participant R as janus-core
  participant D as Data source

  U->>S: Ask a business question
  S->>M: Recall similar NL-SQL pairs (keyword search if embeddings are down)
  S->>M: Fetch relevant schema
  S->>W: Submit SQL against MDL
  W->>P: Load context, plan SQL
  P->>R: Expand MDL semantics
  P->>D: Execute via connector
  D-->>W: Rows
  W-->>U: Rows + provenance + warnings for uncertified models
  S->>M: Store confirmed pair
```

## Core components

### Agent skills

[Skills](/oss/reference/skills) are Markdown workflows that tell AI coding agents how to operate Janus AI safely. They encode procedures such as "build MDL before querying," "fetch context before writing SQL," and "store confirmed examples after success."

Skills sit above the CLI. They do not hide the primitives; they help the agent use them in the right order.

### Janus CLI

The CLI is the main interface for agents and developers. It discovers the project, resolves the active profile, and routes commands to the right subsystem.

| Command | What it does |
| --- | --- |
| `janus query` / `janus --sql` | Plan and execute SQL, then return results. |
| `janus dry-plan` | Plan SQL and show the expanded SQL without executing it. |
| `janus dry-run` | Validate SQL against the live database without returning rows. |
| `janus context` | Initialize, validate, build, and inspect a Janus project. |
| `janus context diff` | Compare the YAML models with the live database and report drift. Exits 1 on drift. |
| `janus context draft` | Draft models for unmodeled tables (`--from-db`, optional `--suggest-terms`); promote one with `apply`. |
| `janus context review` | List, approve, or reject correction proposals made by agents. |
| `janus profile` | Manage database connection profiles. |
| `janus memory` | Index context, fetch schema items, recall examples, and store confirmed queries. |
| `janus utils` | Run helper operations such as type normalization. |

### Project context

A Janus project is the portable context package for one business data layer.

It includes:

- **MDL source files** - models, relationships, views, cubes, and project metadata.
- **`knowledge/`** - business rules (`rules/`) and confirmed NL→SQL pairs (`sql/`), the source of truth for memory.
- **`target/mdl.json`** - compiled MDL manifest used by the engine.
- **`.janus/memory/`** - derived, optional LanceDB index rebuilt from `knowledge/` for semantic retrieval.
- **`knowledge/corrections/`** - correction proposals and their status. Applied and rejected records are kept for audit.
- **`draft/`** - candidate models generated from the database. Not part of the project until applied.

Connection profiles live separately in `~/.janus/profiles.yml` so credentials stay environment-specific.

See the [MDL schema reference](/oss/reference/mdl) for the full project structure.

### Janus Python SDK

The `janusai` Python package exposes the same plan-and-execute pipeline that the CLI drives. The CLI is a thin Typer wrapper over the SDK. Both share the orchestration code, and both can be embedded in agent frameworks, notebooks, and applications.

When invoked (via CLI or SDK), the orchestrator:

1. Receives modeled SQL.
2. Loads the compiled MDL manifest and active connection profile.
3. Calls the SQL planning subsystem (sqlglot + CTE rewrite + janus-core).
4. Sends planned SQL to the correct connector.
5. Returns results as a PyArrow table.

For higher-level integrations, see the [LangChain SDK](/oss/sdk/langchain) and [Pydantic AI SDK](/oss/sdk/pydantic). Both wrap this pipeline as agent tools.

### SQL planning

The SQL planner transforms SQL written against modeled objects into SQL that the target database can execute.

Three pieces collaborate:

- **sqlglot** parses SQL, qualifies table and column references, and transpiles between SQL dialects.
- **CTE rewriter** identifies referenced MDL objects and injects expanded model SQL as CTEs.
- **janus-core** expands MDL semantics: models, relationships, calculated fields, and views.

```text
User SQL against MDL
  |
  |-- parse and qualify SQL
  |-- identify referenced models/views
  |-- extract the relevant MDL manifest slice
  |-- expand models and calculated fields through janus-core
  |-- inject expanded CTEs
  |-- run policy checks
  |-- transpile to the target dialect
  |
  v
Executable SQL for the connected data source
```

### janus-core

`janus-core` is the Rust semantic engine. It is exposed to Python through PyO3 bindings and acts as the source of truth for MDL semantics.

It handles:

- maintaining MDL state in a session context
- extracting only the manifest objects needed for a query
- expanding `table_reference` and `ref_sql` models
- resolving calculated fields
- expanding relationship-aware expressions
- enforcing how modeled objects map to SQL

### Connectors

Connectors execute planned SQL against the target database. Each connector implements a common interface for query execution, dry-run validation, type handling, and connection lifecycle.

Supported data sources include PostgreSQL, MySQL, BigQuery, Snowflake, DuckDB, ClickHouse, Trino, SQL Server, Databricks, Redshift, Oracle, Athena, Apache Spark, and more.

### Memory layer

The [memory system](/oss/concepts/memory_system) is a LanceDB-backed retrieval layer with two primary collections:

| Collection | Contents | Purpose |
| --- | --- | --- |
| `schema_items` | Models, columns, relationships, views, cubes, and instructions | Retrieve the right context for each question. |
| `query_history` | Confirmed natural-language-to-SQL pairs | Recall examples that worked before. |

Memory turns usage into behavioral context. Each confirmed query can become a future example.

## Context maintenance

The context is maintained as YAML in git. Three commands keep it accurate against the database and against agent proposals:

- `janus context diff` compares each model with the live schema. It reports missing or extra columns, type changes, primary-key differences, and tables no model covers. It exits non-zero on drift, so CI can run it.
- `janus context draft --from-db` writes candidate models for unmodeled tables under `draft/`. Nothing in `models/` changes until a person runs `janus context draft apply <model>`.
- Agents do not edit models. `propose_correction` queues a change under `knowledge/corrections/`, and `janus context review approve` applies it after validation.

Models are used only where judgement is needed. Column descriptions (`--suggest-terms`) and semantic recall (`JANUS_EMBEDDING_BACKEND`) can call a model over an OpenAI-compatible API. Each falls back to a deterministic path when the model is missing or fails. Everything else runs without one.

## Data flows

### Query execution

```text
janus --sql "SELECT customer_id, SUM(total) FROM orders GROUP BY 1"
  |
  |-- 1. Discover project: janus_project.yml -> target/mdl.json
  |-- 2. Resolve profile: ~/.janus/profiles.yml
  |-- 3. Plan: parse -> extract MDL -> expand CTEs -> transpile
  |-- 4. Execute: connector -> database -> PyArrow table
  |-- 5. Output: table, CSV, JSON, or SDK return value
```

### Agent-assisted query

```text
User asks a business question
  |
  |-- skill selects the query workflow
  |-- memory recalls similar accepted NL-SQL pairs
  |-- memory fetches relevant schema and instructions
  |-- agent writes SQL against MDL objects
  |-- Janus AI dry-plans, validates, or executes
  |-- agent repairs or asks a clarification if needed
  |-- confirmed answer is stored back into memory
```

### Project build

```text
janus context build
  |
  |-- read janus_project.yml
  |-- read models, views, cubes, and relationships
  |-- validate structure and references
  |-- compile source YAML into target/mdl.json
```

### Memory lifecycle

```text
janus memory index           -> parse MDL and instructions, build schema_items
janus memory fetch -q "..."  -> retrieve relevant schema context
janus memory recall -q "..." -> retrieve similar confirmed examples
janus memory store           -> append a new NL-SQL pair to query_history
```

## Key dependencies

| Dependency | Role |
| --- | --- |
| `janus-core-py` | Python bindings for the Rust semantic engine. |
| `sqlglot` | SQL parsing, qualification, and dialect transpilation. |
| Database connectors | Execution layer for supported data sources. |
| `pyarrow` | Query result representation. |
| `lancedb` | Vector storage for memory. |
| `sentence-transformers` | Local embeddings for memory search. |
| `typer` | CLI framework. |
| `pydantic` | Configuration and connection validation. |

## In short

Janus AI architecture separates context from execution:

- project files define what the data means
- memory retrieves relevant context and examples
- skills tell agents how to operate safely
- the planner and Rust engine turn modeled SQL into executable SQL
- connectors run that SQL against the database

That separation is what makes Janus AI portable, inspectable, and agent-native.

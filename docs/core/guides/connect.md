---
sidebar_label: Connect your database
---

# Connect your database

Janus AI talks to your database through a **profile** — credentials and connection details stored in `~/.janus/profiles.yml`. Once a profile is bound to a project, every CLI command and SDK call uses it.

The flow is the same regardless of which database you use:

1. **Install the connector extra** for your data source.
2. **Create a profile** with `janus profile add` (or let the `onboarding` guide do it).
3. **Bind the profile** to your project with `janus context set-profile`.
4. **Generate the MDL** with the `generate-mdl` guide (or manually).
5. **Start querying.**

If you have an AI coding agent installed, the `/janus` skill drives the whole thing — see [Installation](/oss/get_started/installation).

## Supported data sources

| Data source | Connector extra |
|---|---|
| DuckDB | _(included)_ |
| PostgreSQL | `postgres` |
| MySQL | `mysql` |
| BigQuery | `bigquery` |
| Snowflake | `snowflake` |
| ClickHouse | `clickhouse` |
| Trino / Presto | `trino` |
| SQL Server | `mssql` |
| Databricks | `databricks` |
| Redshift | `redshift` |
| Oracle | `oracle` |
| Athena | `athena` |
| Spark | `spark` |

Install one or more extras together:

```bash
pip install "janusai[postgres,bigquery,main]"
```

## Inspecting connection fields

To see the exact fields required and accepted by a connector, run:

```bash
janus docs connection-info <ds>
```

The output is generated directly from the engine's connection schema, so it always matches the version of `janusai` you have installed. Examples:

```bash
janus docs connection-info postgres
janus docs connection-info bigquery
janus docs connection-info snowflake
```

Use this instead of memorizing field names — the CLI is the source of truth.

## Creating a profile

The browser UI is the easiest way:

```bash
janus profile add my-db --ui
```

Or use the interactive flow:

```bash
janus profile add my-db --interactive
```

Or import from a YAML file (recommended for agent-driven setups so secrets live in `.env`):

```bash
janus profile add my-db --from-file connection.yml
```

## Verifying the connection

```bash
janus profile debug   # show resolved config (secrets masked)
janus --sql "SELECT 1"
```

If the connection fails, check credentials, network reachability, SSL settings, and IP allowlists on the cloud-database side.

## Binding the profile to a project

```bash
cd ~/my-project
janus context set-profile my-db
```

This writes `profile: my-db` and `data_source: <ds>` into `janus_project.yml`. Future commands in this project always use this profile, regardless of which profile is globally active.

## Next steps

- [Model your business](/oss/guides/model) — let the agent scaffold MDL from your schema
- [Refine answer quality](/oss/guides/refine) — close the loop with memory and instructions
- [Manage project](/oss/guides/manage_project) — multi-environment profile workflow

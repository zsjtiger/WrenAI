---
sidebar_label: Manage project
---

# Manage project

A Janus project is the unit of authoring, version control, and deployment for MDL. This recipe covers the lifecycle — initialization, validation, build, profile management, multi-environment workflow, and migration.

## What you'll end up with

- A clean understanding of which files live in the project vs. globally in `~/.janus/`
- The lifecycle commands wired into your editor / CI
- Multiple profiles set up for dev / staging / prod against the same project
- A safe pattern for switching environments without touching secrets

## Project lifecycle

```bash
janus context init              # scaffold a new project in cwd
janus context validate          # check YAML structure (no DB required)
janus context build             # compile YAML to target/mdl.json
janus context upgrade           # upgrade to the latest schema_version
janus context set-profile pg    # bind a connection profile to the project
janus memory index              # index schema + knowledge/ for recall
```

A typical first-time setup:

```bash
mkdir my_project && cd my_project
janus context init
# (edit models/, relationships.yml, knowledge/ — usually agent-driven)
janus context validate
janus context build
janus profile add pg-dev --from-file dev.yml --activate
janus context set-profile pg-dev
janus memory index
janus --sql "SELECT 1"
```

After editing models, rebuild and re-index:

```bash
janus context build
janus memory index
```

## `janus_project.yml` at the project root

```yaml
schema_version: 5
name: my_project
version: "1.0"
catalog: janus
schema: public
data_source: postgres
profile: pg-dev
```

| Field | Purpose |
|---|---|
| `schema_version` | Project layout version (current: **5** — the layout below). Owned by the CLI — bump with `janus context upgrade`. The `knowledge/` base tracks its own version in `knowledge/knowledge.yml`, independent of this one. |
| `name` | Project identifier. |
| `version` | Your own project version (free-form). |
| `catalog` / `schema` | **Janus AI namespace**, not your database catalog/schema. Defaults: `janus` / `public`. |
| `data_source` | Data source type — `postgres`, `bigquery`, etc. Set by `janus context set-profile`. |
| `profile` | The bound connection profile. Set by `janus context set-profile`. |

> The same field names `catalog` and `schema` appear inside each model's `table_reference` to point at the database. Do not confuse the two — see the [MDL schema reference](/oss/reference/mdl) for the full distinction.

## Project layout

`janus context init` scaffolds the current layout (**v5**): per-model and per-view folders, `cubes/` for pre-aggregated semantic objects, a first-class `knowledge/` base, and (added later) GenBI `apps/`.

Everything below lives **in the project** (version-controlled), except `target/` (build output) and `.janus/` (project-local runtime state), which are gitignore-able. Connection credentials and global CLI state live separately under `~/.janus/` (see [Where profiles live](#where-profiles-live)).

```text
my_project/
├── janus_project.yml          # project manifest (fields above)
│
├── models/<name>/            # MDL — one folder per model
│   ├── metadata.yml          #   columns, primary_key, table_reference, …
│   └── ref_sql.sql           #   (optional) SQL-defined model body
├── views/<name>/             # MDL — one folder per view
│   ├── metadata.yml          #   view definition
│   └── sql.yml               #   (optional) statement in a separate file
├── relationships.yml         # MDL — all relationships between models
├── cubes/<name>/             # (optional) pre-aggregation cubes
│   └── metadata.yml          #   base_object, measures, dimensions, …
│
├── knowledge/                # knowledge base (committed)
│   ├── rules/                #   business rules — read by `janus context instructions`
│   ├── glossary/             #   business-term definitions
│   ├── metrics/              #   named metric definitions
│   ├── caveats/              #   data caveats / gotchas
│   ├── sql/                  #   NL→SQL pairs — source of truth for memory
│   └── knowledge.yml         #   knowledge-axis schema_version (decoupled from MDL)
│
├── AGENTS.md                 # AI agent workflow guidance for this project
│
├── apps/<name>/              # (optional) generated GenBI apps — see the GenBI guide
│   ├── index.html            #   app entry point
│   └── mdl.json              #   compiled MDL copied into the app
│
├── target/
│   └── mdl.json              # compiled MDL — `janus context build`
└── .janus/                    # project-local runtime state (gitignore-able)
    ├── memory/               #   LanceDB semantic index over knowledge/sql/ — `janus memory index`
    └── apps.yml              #   GenBI app index — written by `janus genbi register`
```

`knowledge/` carries what the database schema cannot — business rules, glossary terms, named metrics, caveats, and the NL→SQL pairs under `knowledge/sql/` (written by `janus memory store`). It tracks its **own** `schema_version` in `knowledge.yml`, decoupled from the MDL layout version because knowledge and the data model evolve on different cadences. `knowledge/rules/` supersedes the older single-file `instructions.md`, and `knowledge/sql/` supersedes `queries.yml`; both legacy files are still read for back-compat but are no longer scaffolded.

The `memory` extra builds a semantic (embedding) index under `.janus/memory/`; without it, recall falls back to reading `knowledge/sql/*.md` directly — so `knowledge/sql/`, not the index, is the source of truth.

`apps/<name>/` and `.janus/apps.yml` are added by the [GenBI workflow](genbi.md); `.janus/apps.yml` is machine-written via `janus genbi register/remove` — never edit it by hand.

## Profile management

Profiles separate connection credentials from project definitions. The same MDL project can connect to multiple databases by switching profiles.

```bash
janus profile list                  # list all profiles (* marks active)
janus profile add pg-prod --ui      # create via browser form
janus profile switch pg-prod        # change the globally active profile
janus profile debug                 # show resolved config (secrets masked)
janus profile rm old-db             # remove a profile
```

### Where profiles live

```text
~/.janus/profiles.yml      # global, all profiles + active pointer
~/.janus/config.yml        # global CLI preferences, default_project
```

The file is written with `0600` permissions. Secrets use `${ENV_VAR}` interpolation — see [Secrets and `.env` files](#secrets-and-env-files) below.

### Profile vs project at a glance

| | Profile | Project |
|---|---|---|
| **What** | Connection credentials | MDL model definitions |
| **Where** | `~/.janus/profiles.yml` (global) | `<project>/janus_project.yml` + `models/` |
| **Scope** | Shared across all projects | Per-project — version controlled |
| **Secrets** | Contains them | None — safe to commit |

## Multi-environment workflow

A single MDL project can be bound to different profiles for different environments.

### Pattern 1: switch profile globally

```bash
janus profile switch pg-dev      # work against dev
janus profile switch pg-prod     # switch to prod for one query
janus profile switch pg-dev      # back to dev
```

### Pattern 2: bind a profile per project

```bash
cd ~/projects/sales
janus context set-profile pg-prod   # writes profile + data_source into janus_project.yml
```

After binding, every command in this project uses `pg-prod` regardless of the globally active profile. Useful when you have multiple projects open at once.

### Pattern 3: per-shell override

```bash
export JANUS_PROJECT_HOME=~/projects/sales
janus --connection-file ./connection.yml --sql "SELECT 1"
```

Useful for CI jobs that need to point at a specific database without touching `~/.janus/profiles.yml`.

## Secrets and `.env` files

Any profile value can reference `${VAR_NAME}` placeholders. Resolution order (first match wins):

1. `os.environ` — variables exported in your shell
2. `$CWD/.env` — directory you run `janus` from
3. `<project>/.env` — co-located with `janus_project.yml`
4. `~/.janus/.env` — user-global fallback

```yaml
# ~/.janus/profiles.yml
profiles:
  pg-prod:
    datasource: postgres
    host: db.example.com
    port: '5432'
    database: janus
    user: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
```

```bash
# .env (in project root, gitignored)
POSTGRES_USER=paul
POSTGRES_PASSWORD=s3cr3t
```

Rules:

- Names must be **UPPERCASE** (`[A-Z_][A-Z0-9_]*`)
- `$$` escapes a literal dollar sign
- Missing vars fail early with a clear error — no cryptic driver errors

AI coding agents should **never** ask for credentials in chat. The agent writes a profile referencing `${POSTGRES_PASSWORD}` and instructs you to fill the value in `.env` via your editor.

## Migrate from an existing manifest

`janus context init` accepts two import flags, one per external manifest format. Both produce the same janus project layout, ready for `validate` / `build`. They are mutually exclusive.

| Source | Command | When to use |
|---|---|---|
| Janus `mdl.json` (camelCase) | `janus context init --from-mdl /path/to/mdl.json --path my_project` | You have an older `mdl.json` from a previous Janus setup. |
| OSI `semantic_model.yaml` | `janus context init --from-osi /path/to/semantic_model.yaml --data-source postgres --path my_project` | You have an [Open Semantic Interchange](./osi.md) file and want to leave the OSI flow to use Janus-only features (cubes, views, RLAC). |

After either import:

```bash
janus context validate --path my_project
janus context build --path my_project
```

If the target directory already has project files, use `--force` to overwrite.

For `--from-osi`, see the dedicated [OSI guide](./osi.md) — it covers the alternative of keeping OSI as the source of truth (`janus context build --from-osi`) instead of migrating once.

## Upgrade an existing project

When a new layout `schema_version` ships, upgrade with:

```bash
janus context upgrade            # bumps to the latest schema_version
janus context upgrade --to 5     # bump to a specific version
janus context upgrade --dry-run  # preview without writing
```

After upgrade, re-validate and re-build:

```bash
janus context validate
janus context build
```

Some versions add content beyond the automatic restamp — e.g. **v5** introduces
`knowledge/` and makes it the home for business rules and NL→SQL memory, so there are extra
steps to move `instructions.md` and an existing LanceDB index across. Per-version steps live
in the [Migration reference](/oss/reference/migration).

## When to come back here

- Adding a new environment (staging / preview / customer X)
- Onboarding a new teammate (point them at `~/.janus/profiles.yml` setup)
- A schema_version bump shows up in a release
- Migrating from another tool's semantic-layer manifest

## See also

- [MDL schema reference](/oss/reference/mdl) — every field in the project's YAML files
- [Operational reference](/oss/reference/operational) — paths, env vars, and discovery rules
- [Connect your data](./connect.md) — the initial connection step

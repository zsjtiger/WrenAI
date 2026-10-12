---
sidebar_label: Operational reference
---

# Operational reference

Single-page reference for every path, environment variable, and discovery rule Janus AI uses. Bookmark this page if you operate Janus AI across machines, environments, or CI.

## File system layout

### Global (`~/.janus/`)

| Path | Purpose | Created by |
|---|---|---|
| `~/.janus/profiles.yml` | All connection profiles plus the `active` pointer. Permissions: `0600`. | `janus profile add` |
| `~/.janus/config.yml` | CLI preferences. Contains `default_project` if set. | `janus context set-profile`, manual edits |
| `~/.janus/connection_info.json` | Legacy connection fallback (kept for backward compatibility). | Older CLI versions |
| `~/.janus/.env` | User-global `.env` fallback for `${VAR}` interpolation. | Manual |

Override the entire global directory with `JANUS_HOME`.

### Per-project (`<project>/`)

| Path | Purpose | Commit? |
|---|---|---|
| `janus_project.yml` | Project root, `schema_version` pin, bound profile and data source. | ✅ yes |
| `models/<name>/metadata.yml` | Model definitions. | ✅ yes |
| `models/<name>/ref_sql.sql` | Optional separate SQL file for `ref_sql` models. | ✅ yes |
| `views/<name>/metadata.yml` | View definitions. | ✅ yes |
| `views/<name>/sql.yml` | Optional separate `statement` file for views. | ✅ yes |
| `cubes/<name>/metadata.yml` | Cube definitions. | ✅ yes |
| `relationships.yml` | All relationships. | ✅ yes |
| `knowledge/rules/` | LLM-facing business rules (supersedes `instructions.md`). | ✅ yes |
| `knowledge/sql/` | Confirmed NL→SQL pairs — source of truth for memory. | ✅ yes |
| `knowledge/knowledge.yml` | Knowledge-axis `schema_version`. | ✅ yes |
| `instructions.md` | Deprecated — move into `knowledge/rules/` (still read if present). | ⚠️ legacy |
| `queries.yml` | Legacy NL-SQL pairs — superseded by `knowledge/sql/`. | ⚠️ legacy |
| `.env` | Per-project `.env` for `${VAR}` interpolation. | ❌ gitignore |
| `.janus/memory/` | Derived LanceDB index (rebuilt from `knowledge/sql/`). | ❌ gitignore |
| `target/mdl.json` | Compiled MDL manifest (rebuildable). | ❌ gitignore |

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `JANUS_HOME` | Override the global Janus directory. | `~/.janus` |
| `JANUS_PROJECT_HOME` | Skip project walk-up; point directly at a project root. | — (walks up from cwd) |
| `OPENAI_API_KEY` | Required for memory embeddings and the `add-llms-md.js` doc prebuild. | — |
| `CLAUDE_SKILLS_DIR` | Override the skill install directory used by `install.sh`. | `~/.claude/skills` |
| `JANUS_SKILLS_BRANCH` | Override the branch when installing skills via the curl script. | `main` |

Profile values can also reference `${VAR}` from `os.environ` or a `.env` file — see [Resolution order](#env-resolution-order).

## Project discovery

When a `janus` command needs a project (`query`, `memory fetch`, `context build`, etc.), the CLI resolves `<project>` in this order:

1. `--path <path>` flag (explicit)
2. `JANUS_PROJECT_HOME` environment variable
3. Walk up from cwd looking for `janus_project.yml`
4. `default_project` field in `~/.janus/config.yml`

If no project is found, the CLI exits with a clear error and suggests `janus context init` or setting `JANUS_PROJECT_HOME`.

## Profile resolution

When a command needs a connection, the CLI resolves connection info in this order:

1. Explicit `--connection-info '<json>'` flag (highest priority)
2. Explicit `--connection-file <path>` flag
3. **Bound profile** in `janus_project.yml` (`profile: <name>`)
4. **Active profile** in `~/.janus/profiles.yml` (the `active` pointer)
5. Legacy `~/.janus/connection_info.json`

If none are found, the command fails with a connection error.

## `.env` resolution order {#env-resolution-order}

`${VAR}` placeholders in profile YAML are resolved at connection time. The CLI looks up each variable in this order (first match wins; process env beats any `.env`):

1. `os.environ` — variables already exported in your shell
2. `$CWD/.env` — directory you run `janus` from
3. `<project>/.env` — co-located with `janus_project.yml`
4. `~/.janus/.env` — user-global fallback

Rules:

- Names must be **UPPERCASE** (`[A-Z_][A-Z0-9_]*`)
- Lowercase `${foo}` is treated as a literal string
- `$$` escapes a literal dollar sign (`a$$b` becomes `a$b`)
- Missing variables fail early with a clear error — no cryptic driver auth errors

## Skill install paths

The `npx skills add` and `install.sh` paths write skills to one of the following directories, depending on the `--agent` flag:

| Pattern | Used by | Examples |
|---|---|---|
| `<project>/.agents/skills/` | Multi-agent shared dir | Amp, Cursor, Cline, OpenCode (project), Codex (project) |
| `<project>/.<agent>/skills/` | Agent-specific dir | Claude Code (`.claude/skills/`), Continue (`.continue/skills/`), Windsurf (`.windsurf/skills/`) |
| `<project>/skills/` | Repo-root convention | OpenClaw |
| `~/.<agent>/skills/` | Global install | `~/.codex/skills/`, `~/.gemini/skills/`, `~/.deepagents/agent/skills/` |

See [Installation](/oss/get_started/installation) for the per-agent picker.

## Recommended `.gitignore`

For a Janus project, add:

```text
target/
.janus/memory/
.env
```

For an application repo that uses Janus AI through SDK or CLI, also consider:

```text
.janus/                 # if the runtime state directory is created in the repo root
```

## Permissions

| File | Permission |
|---|---|
| `~/.janus/profiles.yml` | `0600` — owner read/write only. Written atomically (temp file + rename). |
| `<project>/.env` | Owner read/write recommended. |
| `~/.janus/.env` | Owner read/write recommended. |

Secrets in `profiles.yml` are kept as `${VAR}` placeholders — the file never contains plaintext credentials. `janus profile debug` masks any fields named `password`, `credentials`, `secret`, or `token`.

## See also

- [CLI reference](./cli.md) — every command and flag
- [MDL schema reference](./mdl.md) — every YAML field in a project
- [Manage project](/oss/guides/manage_project) — lifecycle commands and profile workflow

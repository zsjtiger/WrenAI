# Janus Engine — Agent Skill Distribution

The actual skill content (workflow guides, reference docs, prompt helpers)
**lives inside the `janus` CLI**. This directory ships a single discovery stub
that an AI client installs once; the stub then tells the agent to fetch
everything else from the CLI at runtime (so content always matches the
installed janusai version).

See [`SKILLS.md`](SKILLS.md) for the full design and command surface.

## Install

### The CLI itself (where all skill content lives)

```bash
pip install janusai
```

### The discovery stub (so an AI client knows the CLI exists)

#### Option 1 — Claude Code plugin

```text
/plugin marketplace add CrossNow/JanusAI --path skills
/plugin install janus@janus
```

#### Option 2 — `npx skills`

```bash
npx skills add CrossNow/JanusAI
```

The installer auto-detects your AI client. To target a specific one, add
`--agent <name>` (e.g. `claude-code`, `cursor`, `windsurf`, `cline`).

#### Option 3 — local install script

```bash
bash skills/install.sh                 # install the discovery stub
bash skills/install.sh --force         # overwrite existing
```

## What the agent does with the stub

Once installed, the agent reads `janus/SKILL.md` and learns to call:

```bash
janus skills list                        # discover workflow guides
janus skills get onboarding              # fetch a guide (one of 5 names)
janus docs connection-info <ds>          # connection fields for a data source
janus ask "<question>" --guided|--direct # wrap a prompt for an agent
```

## Requirements

- `janus` CLI installed (`pip install janusai` or `pip install "janusai[<extras>]"`)
- A database connection (configured via `janus profile add`)
- An AI client that supports skills (Claude Code, Cursor, Cline, etc.)

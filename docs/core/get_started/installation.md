---
sidebar_label: Installation
---

# Installation

Get Janus AI running. Your AI coding agent does the rest.

## 1. Install the skill

This installs a single **discovery stub** (`janus`) that teaches AI coding agents (Claude Code, Openclaw, Hermes, Codex, etc.) how to drive the Janus CLI for you:

```bash
npx skills add CrossNow/JanusAI
```

Have multiple AI coding agents installed and want the stub available in all of them? Pass `--agent '*'`:

```bash
npx skills add CrossNow/JanusAI --agent '*'
```

Or via the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/CrossNow/JanusAI/main/skills/install.sh | bash
```

> **Only one skill is installed** — `janus` (at `~/.claude/skills/janus/SKILL.md` for Claude Code). This is expected. Since Janus `0.8`, the workflow guides (`onboarding`, `usage`, `generate-mdl`, `dlt-connector`, `enrich-context`) no longer install as separate skills; they live inside the `janus` CLI and the stub fetches them on demand with `janus skills get <name>`. See the [Skills reference](/oss/reference/skills) for the full delivery model and what each guide does.

## 2. Ask your agent to set things up

**Start a new agent session** (skills load at session start), open your project directory, and ask:

Use the `/janus` skill to install and set up Janus AI.

The agent will check your environment, install Python dependencies, create a connection profile for your data source, scaffold the project, and run a first query — all in one flow.

## 3. Start asking questions

Once onboarding finishes, just ask your agent business questions in natural language. The agent uses Janus AI's context layer to resolve schema, recall similar past queries, and generate accurate SQL.

```text
How many customers placed more than one order this month?
```

```text
What are the top 5 products by total revenue?
```

## What's next

- [Quickstart](./quickstart.md) — walk through a full example with the bundled `jaffle_shop` sample dataset
- [Connect your database](/oss/guides/connect) — connect a profile to a real data source
- [Skills reference](/oss/reference/skills) — what each skill does in detail

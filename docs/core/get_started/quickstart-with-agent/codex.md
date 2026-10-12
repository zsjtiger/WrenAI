---
sidebar_label: Codex
---

# Install Janus AI with Codex

OpenAI Codex CLI.

## Prerequisites

- [Codex](https://developers.openai.com/codex) installed and authenticated.
- OpenAI account login required.

## Install Janus skills

```bash
npx skills add Canner/WrenAI --agent codex
```

## Run onboarding

```bash
codex
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

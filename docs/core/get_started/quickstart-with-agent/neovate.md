---
sidebar_label: Neovate
---

# Install Janus AI with Neovate

Neovate coding agent.

## Prerequisites

- [Neovate](https://github.com/vercel-labs/skills) installed and authenticated.

## Install Janus skills

```bash
npx skills add Canner/WrenAI --agent neovate
```

## Run onboarding

```bash
neovate
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

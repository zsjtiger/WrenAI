---
sidebar_label: Dexto
---

# Install Janus AI with Dexto

Dexto coding agent.

## Prerequisites

- [Dexto](https://github.com/vercel-labs/skills) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent dexto
```

## Run onboarding

Open your project folder in Dexto, then start a new chat session.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

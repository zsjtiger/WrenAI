---
sidebar_label: Hermes Agent
---

# Install Janus AI with Hermes Agent

Hermes coding agent.

## Prerequisites

- [Hermes Agent](https://github.com/vercel-labs/skills) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent hermes-agent
```

## Run onboarding

Open your project folder in Hermes Agent, then start a new chat session.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

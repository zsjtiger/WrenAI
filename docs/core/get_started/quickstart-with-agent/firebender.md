---
sidebar_label: Firebender
---

# Install Janus AI with Firebender

Android JetBrains coding agent.

## Prerequisites

- [Firebender](https://firebender.com) installed and authenticated.
- A JetBrains IDE is required.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent firebender
```

## Run onboarding

Open your project in a JetBrains IDE with the Firebender plugin installed, then open the Firebender chat panel.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

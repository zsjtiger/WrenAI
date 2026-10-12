---
sidebar_label: Junie
---

# Install Janus AI with Junie

JetBrains Junie.

## Prerequisites

- [Junie](https://www.jetbrains.com/junie) installed and authenticated.
- A JetBrains IDE is required.

## Install Janus skills

```bash
npx skills add Canner/WrenAI --agent junie
```

## Run onboarding

Open your project in a JetBrains IDE with the Junie plugin installed, then open the Junie tool window from the right sidebar.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

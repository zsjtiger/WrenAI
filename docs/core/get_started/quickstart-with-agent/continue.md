---
sidebar_label: Continue
---

# Install Janus AI with Continue

Open-source IDE coding assistant.

## Prerequisites

- [Continue](https://continue.dev) installed and authenticated.

## Install Janus skills

```bash
npx skills add Canner/WrenAI --agent continue
```

## Run onboarding

Open your project folder in VS Code or a JetBrains IDE with the Continue extension installed, then open the Continue chat panel (`⌘L` / `Ctrl+L` on VS Code, `⌘J` / `Ctrl+J` on JetBrains).

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

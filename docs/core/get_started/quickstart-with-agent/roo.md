---
sidebar_label: Roo Code
---

# Install Janus AI with Roo Code

VS Code coding agent.

## Prerequisites

- [Roo Code](https://roocode.com) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent roo
```

## Run onboarding

Open your project folder in VS Code with the Roo Code extension installed, then click the Roo icon in the Activity Bar to open the chat panel.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

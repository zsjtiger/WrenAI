---
sidebar_label: Augment
---

# Install Janus AI with Augment

Augment Code coding agent.

## Prerequisites

- [Augment](https://www.augmentcode.com) installed and authenticated.
- Augment account login required.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent augment
```

## Run onboarding

Open your project in VS Code with the Augment extension installed, then open the Augment panel. Or use the CLI:

```bash
auggie
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

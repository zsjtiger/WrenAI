---
sidebar_label: OpenHands
---

# Install Janus AI with OpenHands

All-Hands open-source coding agent.

## Prerequisites

- [OpenHands](https://docs.openhands.ai) installed and authenticated.
- A Docker runtime is typically required.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent openhands
```

## Run onboarding

```bash
openhands
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

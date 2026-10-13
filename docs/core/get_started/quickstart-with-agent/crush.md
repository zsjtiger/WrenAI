---
sidebar_label: Crush
---

# Install Janus AI with Crush

Charm's TUI coding agent.

## Prerequisites

- [Crush](https://github.com/charmbracelet/crush) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent crush
```

## Run onboarding

```bash
crush
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

---
sidebar_label: Devin for Terminal
---

# Install Janus AI with Devin for Terminal

Cognition Devin CLI.

## Prerequisites

- [Devin for Terminal](https://devin.ai) installed and authenticated.
- A Devin subscription is required.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent devin
```

## Run onboarding

```bash
devin
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

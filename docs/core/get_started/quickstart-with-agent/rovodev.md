---
sidebar_label: Rovo Dev
---

# Install Janus AI with Rovo Dev

Atlassian Rovo Dev.

## Prerequisites

- [Rovo Dev](https://www.atlassian.com/software/rovo) installed and authenticated.
- An Atlassian account is required.

## Install Janus skills

```bash
npx skills add Canner/WrenAI --agent rovodev
```

## Run onboarding

```bash
acli rovodev run
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

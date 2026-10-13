---
sidebar_label: Kode
---

# Install Janus AI with Kode

shareAI Kode coding agent.

## Prerequisites

- [Kode](https://github.com/shareAI-lab/kode) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent kode
```

## Run onboarding

```bash
kode
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

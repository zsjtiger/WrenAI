---
sidebar_label: Droid
---

# Install Janus AI with Droid

Factory AI Droid CLI.

## Prerequisites

- [Droid](https://docs.factory.ai/cli) installed and authenticated.
- Factory login required.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent droid
```

## Run onboarding

```bash
droid
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

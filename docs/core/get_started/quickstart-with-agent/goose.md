---
sidebar_label: Goose
---

# Install Janus AI with Goose

Block's open-source coding agent.

## Prerequisites

- [Goose](https://block.github.io/goose) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent goose
```

## Run onboarding

```bash
goose session
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

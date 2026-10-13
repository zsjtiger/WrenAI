---
sidebar_label: Mistral Vibe
---

# Install Janus AI with Mistral Vibe

Mistral's Vibe coding agent.

## Prerequisites

- [Mistral Vibe](https://mistral.ai) installed and authenticated.
- Mistral account login required.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent mistral-vibe
```

## Run onboarding

```bash
vibe
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

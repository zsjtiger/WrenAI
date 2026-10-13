---
sidebar_label: Antigravity
---

# Install Janus AI with Antigravity

Google's AI development workspace.

## Prerequisites

- [Antigravity](https://antigravity.google) installed and authenticated.
- A Google account login is required.

## Install Janus skills

```bash
npx skills add CrossNow/JanusAI --agent antigravity
```

## Run onboarding

Open your project folder in Antigravity, then start a new agent session.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

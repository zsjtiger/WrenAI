---
sidebar_label: Trae CN
---

# Install Janus AI with Trae CN

Trae (China region).

## Prerequisites

- [Trae CN](https://trae.com.cn) installed and authenticated.
- A China-region account is required.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent trae-cn
```

## Run onboarding

Open your project folder in Trae CN IDE (`File → Open Folder...`), then open the chat panel.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

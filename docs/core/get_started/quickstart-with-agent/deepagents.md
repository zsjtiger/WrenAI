---
sidebar_label: Deep Agents
---

# Install Janus AI with Deep Agents

LangChain Deep Agents framework.

## Prerequisites

- [Deep Agents](https://github.com/langchain-ai/deepagents) installed and authenticated.
- Python environment setup required.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent deepagents
```

## Run onboarding

```bash
dcode
```

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

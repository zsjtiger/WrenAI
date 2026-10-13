---
sidebar_label: CodeBuddy
---

# Install Janus AI with CodeBuddy

Tencent CodeBuddy coding agent.

## Prerequisites

- [CodeBuddy](https://www.codebuddy.ai) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent codebuddy
```

## Run onboarding

Open your project in CodeBuddy IDE (or the VS Code extension), then open the CodeBuddy chat panel.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

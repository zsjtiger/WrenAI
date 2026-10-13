---
sidebar_label: Cursor
---

# Install Janus AI with Cursor

The Cursor IDE.

## Prerequisites

- [Cursor](https://cursor.com) installed and authenticated.

## Install Janus skills

```bash
npx skills add CrossNow/janusai --agent cursor
```

## Run onboarding

Open your project folder in Cursor (`File → Open Folder...` or `⌘O` / `Ctrl+O`), then open the chat panel with `⌘L` / `Ctrl+L`.

Then ask:

```text
Use the /janus skill to install and set up Janus AI.
```

The skill walks the agent through environment checks, profile creation, project scaffolding, and a first query.

## Next step

- [Quickstart with sample data](../quickstart) — walk through `jaffle_shop` end-to-end
- [Connect your data](/oss/guides/connect) — point Janus AI at a real database

# Janus AI Core Documentation

🌐 **English** · [简体中文](./zh-CN/README.md)

This directory is the **single source of truth** for Janus AI Core docs published at [docs.crossnow.cn](https://docs.crossnow.cn/oss/introduction).

Changes merged to `main` are automatically synced to the doc website via GitHub Actions (`.github/workflows/sync-docs.yml`). The sync is **additive overlay** — files are copied and overwritten, but nothing is deleted automatically; stale files left behind by source-side renames or deletions must be cleaned up manually in the docs site repo.

## Overview

- [Introduction](introduction.mdx) — what Janus AI Core is, problem it solves, core ideas

## Get Started

- [Installation](get_started/installation.md) — agent-driven or manual CLI install
- [Quickstart](get_started/quickstart.md) — try the bundled `jaffle_shop` demo
- [Connect Your Database](guides/connect.md)

## Concepts

- [What is Context?](concepts/what_is_context.md)
- [What is MDL?](concepts/what_is_mdl.md)
- [Benefits for LLMs](concepts/why_janus.md)
- [Architecture](reference/architecture.md)

## Guides

- [Data Modeling Overview](guides/model.md)
- [Janus Project Structure](internals/project-layout-v5.md)
- [Models](guides/model.md)
- [Relations](guides/model.md)
- [Views](guides/model.md)
- [Memory](concepts/memory_system.md)
- [Profiles](guides/connect.md)
- [dbt Integration](guides/dbt-integration.md)
- [Build & deploy a CReport app](guides/creport.md)

## Reference

- [CLI Reference](reference/cli.md)
- [Skills](reference/skills.md)

## Sync configuration

- [`.sync.yml`](.sync.yml) — declares which files/folders this directory contributes to the docs site
- [`.github/workflows/sync-docs.yml`](../../.github/workflows/sync-docs.yml) — the GitHub Actions workflow that performs the sync

## Not synced

- `README.md` — this file
- `.sync.yml` — sync configuration

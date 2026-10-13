<div align="center" id="top">
<a href="https://crossnow.cn">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./misc/janus-ai-banner-dark.png">
    <img src="./misc/janus-ai-banner.png" width="100%" alt="JanusAI: open-source CReport for AI agents">
  </picture>
</a>

### Open-source CReport for AI agents

**Your agents generate governed SQL, deploy dashboards, and keep business definitions in Git, across 22+ data sources.**

<br/>

**[Get started in 3 commands ↓](#quickstart)** &nbsp;·&nbsp; **[Read the docs →](https://docs.crossnow.cn)** &nbsp;·&nbsp; **[Join Discord →](https://discord.gg/5DvshJqG8Z)**

<br/>

🌐 **English** · [简体中文](./README.zh-CN.md)

<br/>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/CrossNow/JanusAI/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/janusai?label=janusai)](https://pypi.org/project/janusai/)
[![GitHub Release](https://img.shields.io/github/v/release/CrossNow/JanusAI?logo=github&label=release)](https://github.com/CrossNow/JanusAI/releases)
[![Discord](https://img.shields.io/discord/1227143286951514152?logo=discord&label=Discord)](https://discord.gg/5DvshJqG8Z)
[![Follow on X](https://img.shields.io/badge/follow-@getwrenai-blue?logo=x&logoColor=white)](https://x.com/getwrenai)
![Stars](https://img.shields.io/github/stars/CrossNow/JanusAI?style=social)

<a href="https://trendshift.io/repositories/9263" target="_blank"><img src="https://trendshift.io/api/badge/repositories/9263" alt="CrossNow/JanusAI | Trendshift" width="250" height="55" /></a>

</div>

---

## What JanusAI is

JanusAI is the open-source **generative BI (CReport) engine**. It gives the AI agents you already use (Claude Code, Cursor, MCP clients, LangChain) a **governed semantic layer** and an **AI context layer**, so they turn business questions into correct SQL, ship the answer as a shareable dashboard, and stay inside your guardrails.

Schemas tell an agent where data lives. Janus tells it what the data *means*: approved metric definitions, enums, units, joins, worked examples, and the tribal knowledge buried in docs and chat threads. All of it lives as reviewable YAML and Markdown in a repo you own.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./misc/janus-ai-architecture-dark.png">
  <img src="./misc/janus-ai-architecture.png" width="100%" alt="Janus AI generative BI architecture — semantic layer and AI context layer for AI agents">
</picture>

## Quickstart

Three commands, then your agent does the rest. Works with Claude Code, Cursor, Cline, Codex, and [50+ other agents](https://docs.crossnow.cn/oss/get_started/quickstart).

**1. Install the CLI**

```bash
pip install janusai
```

Add connector extras as you need them, for example `pip install "janusai[postgres,memory]"`.

**2. Teach your agent about Janus**

```bash
npx skills add CrossNow/JanusAI
```

This installs a ~50-line discovery stub. Your agent fetches full workflow guides from the CLI on demand, so instructions always match the installed version.

**3. Open your agent in a project folder and ask**

> "Use Janus to set up my Postgres database."

The agent checks your environment, creates a connection profile, scaffolds the project, and runs a first query.

**No database handy?** Say "Use Janus with the bundled `jaffle_shop` sample" and run the same flow against a real sample warehouse.

<details>
<summary>Slow <code>pip install</code> from mainland China?</summary>

```bash
pip install janusai -i https://pypi.tuna.tsinghua.edu.cn/simple
```

If HuggingFace model downloads time out, run `export HF_ENDPOINT=https://hf-mirror.com` before using the CLI.

</details>

### Then keep going

Once you're connected, these three prompts cover the whole CReport loop:

| Beat | Ask your agent | What happens |
|---|---|---|
| **Know** | "Enrich my Janus project with the business context in `raw/`." | Runs `janus skills get enrich-context`. Writes definitions, examples, and memory as reviewable files. |
| **Generate** | "Who are our top 10 customers by sales this quarter?" | Recalls MDL context and past queries, writes governed SQL, executes via `janus query`. |
| **Deploy** | "Turn that into a dashboard I can filter and share, deployed to Vercel." | Runs `janus skills get creport`. Builds a browser-side app and returns a live URL on your Vercel or Cloudflare Pages account. |

<div align="center">

**[Follow the full quickstart →](https://docs.crossnow.cn/oss/get_started/quickstart)**

</div>

## License

Apache 2.0. See [LICENSE](./LICENSE).

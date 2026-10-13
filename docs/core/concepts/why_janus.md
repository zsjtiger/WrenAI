---
sidebar_label: Why Janus? (and how it compares)
---

# Why Janus? (and how it compares)

Janus AI is the **CReport engine**: it lets AI agents generate, deploy,
and govern business intelligence on top of a context layer they can trust. This
page is the honest version: what Janus is for, what it is *not*, and how it
differs from the tools it sits near.

## The problem Janus solves

Agents are everywhere: Claude Code, Cursor, ChatGPT, Aider, LangChain
pipelines, in-house copilots. None of them know what your data *means*. Point one
at a warehouse and it writes confident, plausible, wrong SQL, because the meaning
it needs (canonical tables, approved definitions, units, join paths) lives
outside the schema. Build a dashboard on top of that and you have shipped a
trustworthy-looking lie.

Janus gives every agent the same governed context, then lets them turn questions
into answers and dashboards that are actually correct.

## How Janus compares

|  | A raw LLM agent | A traditional BI tool | A bare semantic layer | **Janus AI** |
| --- | :---: | :---: | :---: | :---: |
| Writes SQL for you | ✅ (often wrong) | ❌ | ❌ | ✅ governed |
| Knows your business definitions | ❌ | partial, in-tool | ✅ (schema-derived) | ✅ + non-schema knowledge |
| Generates **and** deploys dashboards | ❌ | ✅ (manual, in-tool) | ❌ | ✅ agent-driven |
| Works through *your* agents (Claude Code, Cursor, MCP…) | ✅ | ❌ | ❌ | ✅ |
| Open, reviewable, Git-friendly context | ❌ | ❌ | partial | ✅ |
| Governed execution across 22+ sources | ❌ | per-connector | ✅ (definitions only) | ✅ |

A few distinctions worth being precise about:

- **vs. a raw LLM agent:** Janus is the governance and knowledge the agent is
  missing. Same agent, correct answers.
- **vs. a traditional BI tool:** BI tools render dashboards a human builds by
  hand, in their UI. Janus has agents *generate* them from your context and
  deploy them to your own hosting.
- **vs. a bare semantic layer** (dbt Semantic Layer, Cube): those define metrics
  from the schema. Janus's context layer adds the company knowledge that isn't in the schema
  (enum meanings, units, policy, proven examples) and a generative-BI output on
  top. See [How does the agent learn from your context?](/oss/concepts/agent_learning).

## Janus is for you if…

- You want **AI agents to produce trustworthy BI** (answers *and* dashboards),
  not just plausible SQL.
- Your business logic lives **outside the database** and your agents keep
  getting it wrong.
- You want context that's **open, reviewable, and version-controlled**, usable
  by every agent and person, not gated behind one vendor's UI.
- You query **many sources** (Postgres, BigQuery, Snowflake, DuckDB, and 18+
  more) and want one governed surface across them.

## Skip Janus if…

- You only need a one-off chart from a single CSV.
- You're happy letting an agent guess at SQL with no governance.
- You want a fully hosted, click-to-build BI product with no setup. In that
  case look at [Janus AI Commercial](https://crossnow.cn).

## Where to go next

- [Install](/oss/get_started/installation) and the [Quickstart](/oss/get_started/quickstart)
- [What does Janus AI mean by context?](/oss/concepts/what_is_context): the idea underneath CReport

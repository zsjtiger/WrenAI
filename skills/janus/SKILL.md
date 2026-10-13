---
name: janus
description: "Janus CLI for AI agents — a semantic SQL layer over 22+ databases (Postgres, MySQL, BigQuery, Snowflake, Spark, …). The actual workflow guides live inside the `janus` CLI itself; this is just a discovery stub. Use whenever the user asks a data question (how many, show me, top N, compare, trend, breakdown, metric, revenue, customers, orders), wants to install / set up Janus Engine, connect a new database, connect SaaS data via dlt (HubSpot, Stripe, Salesforce, GitHub, Slack), generate or regenerate an MDL project from a database schema, enrich a project with business context (enum meanings, units, cubes like ARR / DAU / churn), or turn a project's context layer into a shareable GenBI web app / dashboard and deploy it to Vercel or Cloudflare. Triggers: 'install janus', 'set up janus engine', 'connect database to janus', 'connect SaaS to janus', 'load hubspot / stripe / salesforce data', 'generate mdl', 'scaffold janus project', 'enrich janus context', 'augment my project', 'add cubes', 'build a dashboard', 'make a shareable analytics app', 'deploy my context layer as a web app', 'genbi app', 'janus onboarding', 'janus usage', 'janus generate mdl', 'janus dlt connector', 'janus enrich context', 'janus genbi'."
license: Apache-2.0
allowed-tools: Bash(janus:*)
---

# Janus CLI

This is a discovery stub. The actual workflow guides and prompt helpers
live inside the `janus` CLI itself, so they always match the installed
janusai version (no skill cache, no version drift).

Install: `pip install janusai`.

## Workflow guides

```bash
janus skills list                        # all available workflow guides
janus skills get onboarding              # set up Janus end-to-end
janus skills get usage                   # day-to-day querying
janus skills get generate-mdl            # generate MDL from a database schema
janus skills get dlt-connector           # connect SaaS sources via dlt
janus skills get enrich-context          # add business context (units, enums, cubes)
janus skills get genbi                   # build & deploy a shareable GenBI web app
# add --full to include the skill's reference docs
# add --script <name> to fetch a bundled script (e.g. dlt-connector / introspect_dlt)
```

## Reference docs

Full reference docs live on the web: <https://github.com/CrossNow/janusai/tree/main/docs/core>

```bash
janus docs connection-info <ds>          # required + optional connection fields for a data source
```

## Prompt enhancement (wraps a user question for an agent)

```bash
janus ask "<question>" --guided          # for weaker LLMs (strict task flow)
janus ask "<question>" --direct          # for stronger LLMs (minimal wrapping)
```

## Day-to-day data commands (not a sub-app — top-level)

```bash
janus --sql '...'                        # execute SQL through the MDL layer
janus query --sql '...'                  # same, explicit
janus dry-plan --sql '...'               # transpile only, no DB hit
janus context show / build / validate    # project / MDL lifecycle
janus profile add / list / switch        # named connection profiles
janus memory index / recall / store      # semantic memory (needs `[memory]` extra)
```

Run `janus --help` for the full surface; load the matching `janus skills get
<name>` guide before driving any multi-step workflow.

# Janus Engine — Agent Skills

The actual workflow guides, reference docs, and prompt helpers live **inside
the `janus` CLI itself**, so they always match the installed janusai
version (no skill cache, no version drift).

This directory ships a single discovery stub ([`janus/SKILL.md`](janus/SKILL.md))
that an AI client can install. Once the agent reads the stub, it learns to
fetch everything else from the CLI on demand:

```bash
janus skills list                        # all available workflow guides
janus skills get <name>                  # fetch a guide
janus skills get <name> --full           # include the guide's reference docs
janus skills get <name> --script <s>     # fetch a bundled script

janus docs connection-info <ds>          # connection fields for a data source

janus ask "<question>" --guided          # wrap a question for a weaker LLM
janus ask "<question>" --direct          # wrap a question for a stronger LLM
```

## Install

```bash
pip install janusai                 # the CLI (everything is here)
npx skills add CrossNow/JanusAI            # install the discovery stub for AI clients
```

Or via Claude Code's plugin marketplace:

```text
/plugin marketplace add CrossNow/JanusAI --path skills
/plugin install janus@janus
```

## Writing a new skill

New skill guides ship as Python package data in
[`core/janus/src/janus/skills_content/<name>/`](../core/janus/src/janus/skills_content/),
not as a new directory under this `skills/` tree. See
[`AUTHORING.md`](AUTHORING.md).

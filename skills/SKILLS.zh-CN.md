# Janus 引擎 — Agent 技能

🌐 [English](./SKILLS.md) · **简体中文**

实际的工作流指南、参考文档和提示辅助工具**位于 `janus` CLI 内部**，因此它们始终与已安装的 janusai 版本保持一致（没有技能缓存，也不会出现版本漂移）。

本目录提供一个发现用的桩文件（[`janus/SKILL.md`](janus/SKILL.md)），AI 客户端可以安装它。智能体读取该桩文件后，便会学会按需从 CLI 获取其余内容：

```bash
janus skills list                        # all available workflow guides
janus skills get <name>                  # fetch a guide
janus skills get <name> --full           # include the guide's reference docs
janus skills get <name> --script <s>     # fetch a bundled script

janus docs connection-info <ds>          # connection fields for a data source

janus ask "<question>" --guided          # wrap a question for a weaker LLM
janus ask "<question>" --direct          # wrap a question for a stronger LLM
```

## 安装

```bash
pip install janusai                 # the CLI (everything is here)
npx skills add CrossNow/JanusAI            # install the discovery stub for AI clients
```

也可以通过 Claude Code 的插件市场安装：

```text
/plugin marketplace add CrossNow/JanusAI --path skills
/plugin install janus@janus
```

## 编写新技能

新的技能指南作为 Python 包数据随 [`core/janus/src/janus/skills_content/<name>/`](../core/janus/src/janus/skills_content/) 一同发布，而不是作为本 `skills/` 目录树下的新目录。参见 [`AUTHORING.md`](AUTHORING.zh-CN.md)。

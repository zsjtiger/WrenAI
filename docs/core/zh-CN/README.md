# Janus AI Core 文档（中文）

本目录是 Janus AI Core 中文文档的**当前版本**，对应 [docs.crossnow.cn](https://docs.crossnow.cn/oss/introduction) 上的英文站点。中文文档已覆盖全部英文页面，英文文档仍是权威版本。

🌐 [English](../README.md) · **简体中文**

## 概览

- [介绍](introduction.mdx)：Janus AI Core 是什么、解决什么问题、核心理念

## 中文版本状态

| 部分 | 页面 | 状态 |
|---|---|---|
| 介绍 | [introduction.mdx](introduction.mdx) | ✅ 已翻译 |
| 快速开始 | [安装](get_started/installation.md)、[快速开始](get_started/quickstart.md) | ✅ 已翻译 |
| 指南 | [连接数据库](guides/connect.md)、[建模](guides/model.md)、[Cube 预聚合](guides/cubes.md)、[MCP 服务器](guides/mcp.md)、[CReport 应用](guides/creport.md) | ✅ 已翻译 |
| 指南 | [提升回答质量](guides/refine.md)、[项目管理](guides/manage_project.md)、[dbt 集成](guides/dbt-integration.md)、[OSI](guides/osi.md) | ✅ 已翻译 |
| 概念 | [为什么选择 Janus](concepts/why_janus.md)、[上下文](concepts/what_is_context.md)、[MDL](concepts/what_is_mdl.md)、[记忆](concepts/memory_system.md)、[正确性](concepts/correctness.md) 等 | ✅ 已翻译 |
| 参考 | [CLI](reference/cli.md)、[MDL Schema](reference/mdl.md) | ✅ 已翻译 |
| 参考 | [Skills](reference/skills.md) | ✅ 已翻译 |
| 参考 | [架构](reference/architecture.md)、[迁移](reference/migration.md)、[运维参考](reference/operational.md) | ✅ 已翻译 |
| SDK | [概览](sdk/overview.md)、[LangChain](sdk/langchain.md)、[Pydantic AI](sdk/pydantic.md)、[WASM](sdk/wasm.md) | ✅ 已翻译 |
| 快速开始（Agent 配置） | `get_started/quickstart-with-agent/` 下按 Agent 分别的配置页 | ✅ 已翻译 |

## 注意

- 本目录**不会**被 `sync-docs` 工作流同步到文档站点，因为它不在 `.sync.yml` 的 `sync_dirs` 中。中文页面的发布需要单独的同步配置。
- 代码块中的命令、参数、配置和 API 名称保持英文原样，以便与代码保持一致。代码块中的注释已翻译为中文。

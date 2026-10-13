# Janus AI Core 文档（中文）

本目录是 Janus AI Core 中文文档的**当前版本**，对应 [docs.crossnow.cn](https://docs.crossnow.cn/oss/introduction) 上的英文站点。英文文档仍是权威版本，中文文档尚未全部翻译。

🌐 [English](../README.md) · **简体中文**

## 概览

- [介绍](introduction.mdx)：Janus AI Core 是什么、解决什么问题、核心理念

## 中文版本状态

| 部分 | 页面 | 状态 |
|---|---|---|
| 介绍 | [introduction.mdx](introduction.mdx) | ✅ 已翻译 |
| 快速开始 | [安装](get_started/installation.md) | ✅ 已翻译（快速开始正文仍待翻译） |
| 指南 | [连接数据库](guides/connect.md)、[建模](guides/model.md)、[Cube 预聚合](guides/cubes.md)、[MCP 服务器](guides/mcp.md)、[CReport 应用](guides/creport.md) | ✅ 已翻译 |
| 指南 | 提升回答质量、项目管理、dbt 集成、OSI | ⏳ 待翻译（见英文版） |
| 概念 | 上下文、MDL、记忆、正确性等 | ⏳ 待翻译（见英文版） |
| 参考 | [CLI](reference/cli.md) | ✅ 已翻译 |
| 参考 | MDL、Skills、架构、迁移、运维 | ⏳ 待翻译（见英文版） |
| SDK | 概览、LangChain、Pydantic AI、WASM | ⏳ 待翻译（见英文版） |
| 快速开始（Agent 配置） | `get_started/quickstart-with-agent/` | ⏳ 待翻译（按 Agent 分别的配置页，共 50+ 个） |

在英文页面翻译完成之前，中文页面中指向未翻译页面的链接会指向英文站点（`/oss/...`），以保证链接有效。

## 注意

- 本目录**不会**被 `sync-docs` 工作流同步到文档站点，因为它不在 `.sync.yml` 的 `sync_dirs` 中。中文页面的发布需要单独的同步配置。
- 代码块中的命令、参数、配置和 API 名称保持英文原样，以便与代码保持一致。代码块中的注释已翻译为中文。

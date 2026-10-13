---
sidebar_label: 安装
---

# 安装

让 Janus AI 运行起来，剩下的由你的 AI 编码智能体完成。

## 1. 安装 Skill

这会安装一个**发现存根**（`janus`），让 AI 编码智能体（Claude Code、Openclaw、Hermes、Codex 等）知道如何为你驱动 Janus CLI：

```bash
npx skills add CrossNow/JanusAI
```

如果你安装了多个 AI 编码智能体，并且希望在所有智能体中都可以使用这个存根，请传入 `--agent '*'`：

```bash
npx skills add CrossNow/JanusAI --agent '*'
```

或者通过安装脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/CrossNow/JanusAI/main/skills/install.sh | bash
```

> **只会安装一个 Skill**：`janus`（在 Claude Code 中位于 `~/.claude/skills/janus/SKILL.md`）。这是预期行为。从 Janus `0.8` 开始，工作流指南（`onboarding`、`usage`、`generate-mdl`、`dlt-connector`、`enrich-context`）不再作为单独的 Skill 安装，而是内置在 `janus` CLI 中，存根会在需要时通过 `janus skills get <name>` 获取。完整的交付方式以及每个指南的用途，请参见 [Skills 参考](/oss/reference/skills)。

## 2. 让智能体完成设置

**开启一个新的智能体会话**（Skill 在会话开始时加载），打开你的项目目录，然后提问：

使用 `/janus` Skill 安装并设置 Janus AI。

智能体会检查你的环境、安装 Python 依赖、为你的数据源创建连接配置文件、搭建项目结构，并运行第一条查询，整个流程一次完成。

## 3. 开始提问

设置完成后，直接用自然语言向智能体提出业务问题即可。智能体会借助 Janus AI 的上下文层解析 Schema、检索相似的历史查询，并生成准确的 SQL。

```text
本月下过一单以上订单的客户有多少？
```

```text
按总收入排名，前 5 名的产品是哪些？
```

## 接下来

- [快速开始](/oss/get_started/quickstart)：使用内置的 `jaffle_shop` 示例数据完整走一遍（英文版）
- [连接你的数据库](../guides/connect.md)：把连接配置文件接入真实数据源
- [Skills 参考](/oss/reference/skills)：每个 Skill 的详细说明

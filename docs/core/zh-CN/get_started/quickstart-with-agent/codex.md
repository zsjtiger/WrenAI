---
sidebar_label: Codex
---

# 使用 Codex 安装 Janus AI

OpenAI Codex 命令行工具。

## 前提条件

- 已安装并完成身份验证的 [Codex](https://developers.openai.com/codex)。
- 需要登录 OpenAI 账号。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent codex
```

## 运行引导流程

```bash
codex
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

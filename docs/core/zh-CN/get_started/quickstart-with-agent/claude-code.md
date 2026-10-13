---
sidebar_label: Claude Code
---

# 使用 Claude Code 安装 Janus AI

Anthropic 官方的终端编程助手。

## 前提条件

- 已安装并完成身份验证的 [Claude Code](https://claude.com/code)。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent claude-code
```

## 运行引导流程

```bash
claude
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

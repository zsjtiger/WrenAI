---
sidebar_label: Kimi Code CLI
---

# 使用 Kimi Code CLI 安装 Janus AI

Moonshot Kimi CLI。使用共享的 `.agents/skills/` 目录。

## 前置条件

- [Kimi Code CLI](https://moonshotai.github.io/kimi-cli) 已安装并完成身份验证。
- 需要 Moonshot API 密钥。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent kimi-cli
```

## 运行入门引导

```bash
kimi
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

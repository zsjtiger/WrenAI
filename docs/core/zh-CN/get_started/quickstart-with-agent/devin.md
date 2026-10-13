---
sidebar_label: Devin for Terminal
---

# 使用 Devin for Terminal 安装 Janus AI

Cognition Devin CLI。

## 前置条件

- [Devin for Terminal](https://devin.ai) 已安装并完成身份验证。
- 需要 Devin 订阅。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent devin
```

## 运行入门引导

```bash
devin
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

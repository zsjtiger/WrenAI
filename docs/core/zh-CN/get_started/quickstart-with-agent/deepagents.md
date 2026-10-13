---
sidebar_label: Deep Agents
---

# 使用 Deep Agents 安装 Janus AI

LangChain Deep Agents 框架。

## 前置条件

- [Deep Agents](https://github.com/langchain-ai/deepagents) 已安装并完成身份验证。
- 需要配置 Python 环境。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent deepagents
```

## 运行入门引导

```bash
dcode
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

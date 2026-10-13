---
sidebar_label: Code Studio
---

# 使用 Code Studio 安装 Janus AI

OPPO/Heytap 编程 IDE。

## 前提条件

- 已安装并完成身份验证的 [Code Studio](https://github.com/vercel-labs/skills)。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent codestudio
```

## 运行引导流程

在 Code Studio 中打开你的项目文件夹，然后开始新的对话会话。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

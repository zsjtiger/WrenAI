---
sidebar_label: Warp
---

# 使用 Warp 安装 Janus AI

Warp 终端编程智能体。使用共享的 `.agents/skills/` 目录。

## 前提条件

- [Warp](https://warp.dev) 已安装并完成身份验证。
- 已安装 Warp 应用，并且需要启用 Skills 功能。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent warp
```

## 运行初始化引导

打开 Warp，然后按 `⌘I` / `Ctrl+I` 进入 Agent 模式。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目结构搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart)：使用 `jaffle_shop` 完整走一遍
- [连接你的数据](/oss/guides/connect)：将 Janus AI 指向真实数据库

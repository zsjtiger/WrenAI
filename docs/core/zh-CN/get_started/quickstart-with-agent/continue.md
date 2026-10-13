---
sidebar_label: Continue
---

# 使用 Continue 安装 Janus AI

开源 IDE 编程助手。

## 前提条件

- 已安装并完成身份验证的 [Continue](https://continue.dev)。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent continue
```

## 运行引导流程

在已安装 Continue 扩展的 VS Code 或 JetBrains IDE 中打开你的项目文件夹，然后打开 Continue 对话面板（VS Code 中为 `⌘L` / `Ctrl+L`，JetBrains 中为 `⌘J` / `Ctrl+J`）。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

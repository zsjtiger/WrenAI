---
sidebar_label: Cursor
---

# 使用 Cursor 安装 Janus AI

Cursor IDE。

## 前提条件

- 已安装并完成身份验证的 [Cursor](https://cursor.com)。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent cursor
```

## 运行引导流程

在 Cursor 中打开你的项目文件夹（`File → Open Folder...` 或 `⌘O` / `Ctrl+O`），然后用 `⌘L` / `Ctrl+L` 打开对话面板。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

---
sidebar_label: GitHub Copilot
---

# 使用 GitHub Copilot 安装 Janus AI

GitHub Copilot CLI / Coding Agent。

## 前置条件

- [GitHub Copilot](https://github.com/features/copilot) 已安装并完成身份验证。
- 需要 Copilot 订阅。智能体技能可能仍处于预览阶段，需要账户获得访问权限。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent github-copilot
```

## 运行入门引导

在安装了 GitHub Copilot 的 VS Code（或其他受支持的 IDE）中打开你的项目文件夹，然后使用 `⌃⌘I` / `Ctrl+Alt+I` 打开 Copilot Chat。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

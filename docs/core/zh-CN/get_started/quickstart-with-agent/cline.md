---
sidebar_label: Cline
---

# 使用 Cline 安装 Janus AI

适用于 VS Code 的开源自主编程智能体。

## 前提条件

- 已安装并完成身份验证的 [Cline](https://cline.bot)。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent cline
```

## 运行引导流程

在已安装 Cline 扩展的 VS Code 中打开你的项目文件夹，然后点击活动栏中的 Cline 图标，打开对话面板。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

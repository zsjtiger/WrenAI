---
sidebar_label: Augment
---

# 使用 Augment 安装 Janus AI

Augment Code 编程智能体。

## 前提条件

- 已安装并完成身份验证的 [Augment](https://www.augmentcode.com)。
- 需要登录 Augment 账号。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent augment
```

## 运行引导流程

在已安装 Augment 扩展的 VS Code 中打开你的项目，然后打开 Augment 面板。或者使用命令行工具：

```bash
auggie
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

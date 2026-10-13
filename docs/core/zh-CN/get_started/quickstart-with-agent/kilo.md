---
sidebar_label: Kilo Code
---

# 使用 Kilo Code 安装 Janus AI

VS Code 编码智能体（Roo Code 的分支）。

## 前置条件

- [Kilo Code](https://kilocode.ai) 已安装并完成身份验证。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent kilo
```

## 运行入门引导

在安装了 Kilo Code 扩展的 VS Code 中打开你的项目文件夹，然后点击活动栏中的 Kilo 图标。也可以使用 CLI：

```bash
kilo
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

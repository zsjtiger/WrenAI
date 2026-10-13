---
sidebar_label: Junie
---

# 使用 Junie 安装 Janus AI

JetBrains Junie。

## 前置条件

- [Junie](https://www.jetbrains.com/junie) 已安装并完成身份验证。
- 需要 JetBrains IDE。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent junie
```

## 运行入门引导

在安装了 Junie 插件的 JetBrains IDE 中打开你的项目，然后从右侧边栏打开 Junie 工具窗口。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端地走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 指向真实数据库

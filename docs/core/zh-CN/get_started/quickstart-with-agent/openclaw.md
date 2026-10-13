---
sidebar_label: OpenClaw
---

# 使用 OpenClaw 安装 Janus AI

OpenClaw 编程智能体。

## 前提条件

- [OpenClaw](https://openclaw.ai) 已安装并完成身份验证。
- 项目级技能安装在仓库根目录的 `skills/` 下，**而不是**隐藏的 `.openclaw/` 目录下。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent openclaw
```

## 运行初始化引导

```bash
openclaw
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目结构搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart)：使用 `jaffle_shop` 完整走一遍
- [连接你的数据](/oss/guides/connect)：将 Janus AI 指向真实数据库

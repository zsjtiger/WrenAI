---
sidebar_label: CodeArts Agent
---

# 使用 CodeArts Agent 安装 Janus AI

华为云 CodeArts Doer。

## 前提条件

- 已安装并完成身份验证的 [CodeArts Agent](https://www.huaweicloud.com/product/codeartsdoer.html)。
- 需要华为云账号。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent codearts-agent
```

## 运行引导流程

在 CodeArts IDE 中打开你的项目，然后打开 CodeArts Agent 面板。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目脚手架搭建和首次查询。

## 下一步

- [使用示例数据快速开始](../quickstart) — 端到端走通 `jaffle_shop`
- [连接你的数据](/oss/guides/connect) — 将 Janus AI 连接到真实数据库

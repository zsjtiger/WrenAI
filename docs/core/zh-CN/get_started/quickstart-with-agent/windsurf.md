---
sidebar_label: Windsurf
---

# 使用 Windsurf 安装 Janus AI

Codeium Windsurf IDE。

## 前提条件

- [Windsurf](https://windsurf.com) 已安装并完成身份验证。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent windsurf
```

## 运行初始化引导

在 Windsurf 中打开你的项目文件夹（`File → Open Folder...`），然后从右侧边栏打开 Cascade 面板（`⌘L` / `Ctrl+L`）。

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目结构搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart)：使用 `jaffle_shop` 完整走一遍
- [连接你的数据](/oss/guides/connect)：将 Janus AI 指向真实数据库

---
sidebar_label: Qwen Code
---

# 使用 Qwen Code 安装 Janus AI

阿里巴巴 Qwen Code 命令行工具。

## 前提条件

- [Qwen Code](https://qwenlm.github.io/qwen-code-docs) 已安装并完成身份验证。
- 需要 Qwen API 访问权限。

## 安装 Janus 技能

```bash
npx skills add CrossNow/JanusAI --agent qwen-code
```

## 运行初始化引导

```bash
qwen
```

然后提问：

```text
Use the /janus skill to install and set up Janus AI.
```

该技能会引导智能体完成环境检查、配置文件创建、项目结构搭建以及第一条查询。

## 下一步

- [使用示例数据快速开始](../quickstart)：使用 `jaffle_shop` 完整走一遍
- [连接你的数据](/oss/guides/connect)：将 Janus AI 指向真实数据库

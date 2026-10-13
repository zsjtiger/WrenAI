<div align="center" id="top">
<a href="https://crossnow.cn">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./misc/janus-ai-banner-dark.png">
    <img src="./misc/janus-ai-banner.png" width="100%" alt="JanusAI：面向 AI 智能体的开源 CReport">
  </picture>
</a>

### 面向 AI 智能体的开源 CReport

**让你的智能体生成受治理的 SQL、部署仪表盘，并把业务定义保存在 Git 中，覆盖 22+ 种数据源。**

<br/>

🌐 [English](./README.md) · **简体中文**

<br/>

</div>

---

## JanusAI 是什么

JanusAI 是开源的**生成式 BI（CReport）引擎**。它为你已经在用的 AI 智能体（Claude Code、Cursor、MCP 客户端、LangChain）提供一个**受治理的语义层**和一个 **AI 上下文层**，让它们把业务问题转换为正确的 SQL、把结果发布为可分享的仪表盘，并始终处在你设定的护栏之内。

Schema 只能告诉智能体数据存放在哪里。Janus 则告诉它数据**意味着什么**：经过批准的指标定义、枚举值、单位、关联关系、示例，以及埋在文档和聊天记录里的隐性知识。这些内容都以可审阅的 YAML 和 Markdown 文件保存在你自己的代码仓库中。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./misc/janus-ai-architecture-dark.png">
  <img src="./misc/janus-ai-architecture.png" width="100%" alt="Janus AI 生成式 BI 架构：面向 AI 智能体的语义层与 AI 上下文层">
</picture>

## 快速开始

三条命令，剩下的交给你的智能体。支持 Claude Code、Cursor、Cline、Codex，以及 [50+ 其他智能体](https://docs.crossnow.cn/oss/get_started/quickstart)。

**1. 安装 CLI**

```bash
pip install janusai
```

按需添加连接器依赖，例如 `pip install "janusai[postgres,memory]"`。

**2. 让你的智能体了解 Janus**

```bash
npx skills add CrossNow/JanusAI
```

这会安装一个约 50 行的发现存根。智能体会按需从 CLI 获取完整的工作流指南，因此说明始终与已安装的版本一致。

**3. 在项目目录中打开你的智能体并提问**

> "用 Janus 帮我设置 Postgres 数据库。"

智能体会检查环境、创建连接配置文件、搭建项目结构，并运行第一条查询。

**手边没有数据库？** 直接说"用 Janus 配合内置的 `jaffle_shop` 示例数据"，同样的流程就会在一个真实的示例数据仓库上运行。

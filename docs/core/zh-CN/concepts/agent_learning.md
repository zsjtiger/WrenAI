---
sidebar_label: 智能体如何从你的上下文中学习？
---

# 智能体如何从你的上下文中学习？

> 能够投入生产的智能体，并不是把你的业务"背下来"的。它读取结构化的上下文，召回经过验证的示例，并在工作过程中把新的学习成果写回去。Janus AI 正是围绕这一闭环设计的，它也使智能体为你生成的 BI 随时间变得越来越正确。

## 为什么这很重要

入职第一天的分析师并不知道哪张表是权威的，智能体也一样。两者都通过同一条路径变得更好：有指导地开始、聚焦的提问，以及对什么有效的记录。

区别在于，除非你的工具把学习成果保存在可审阅的地方，否则智能体会在会话之间遗忘它。Janus AI 把这些学习成果保存在四个显式的位置（MDL、业务规则、经过确认的自然语言到 SQL 配对，以及记忆索引），使智能体每次都能从团队上次停下的地方接着做。

## 两个阶段：快速搭建，深度丰富

每当你设置一个新项目时，Janus AI 都会引导智能体经历两个阶段。

**第一阶段：快速搭建。** `generate-mdl` 指南引导智能体完成 Schema 发现、类型规范化以及初始的 MDL 项目。几分钟之内，智能体就可以通过这一建模层进行查询了。MDL 虽然粗糙但可以用，它涵盖了数据库能够告诉你的关于它自身的信息。

**第二阶段：深度丰富。** 结构只是起点。真正困难的业务含义存在于文档、幻灯片、Slack 讨论串和分析师编写的 SQL 之中。`enrich-context` 工作流通过两种模式引入这些含义：

- **追问模式（Grill mode）**：智能体每次提出一个聚焦的问题（"哪张是权威的 `orders` 表？"、"`status = 4` 是什么意思？"、"`active customer` 是否应排除内部用户？"）。你回答，智能体随后修改 MDL 或 `knowledge/`（规则和自然语言到 SQL 配对）。
- **自动驾驶模式（Auto-pilot mode）**：把 PDF、术语表、手册和 SQL 历史放入 `<project>/raw/`。智能体读取这些材料，附带证据提出上下文变更建议，并等待审阅。

两种模式都会写入可审阅、受版本控制的产物。没有任何内容会被悄无声息地吸收到黑盒中。

## 学习成果存放在哪里

四类产物分别记录不同层次的学习成果——都是显式、可检查的文件，而不是提示词或锁定的 UI：

| 产物 | 保存的内容 | 示例 | 更新方式 |
|---|---|---|---|
| **MDL**（`models/`、`views/`、`relationships.yml`） | 结构和语义契约：存在哪些数据、它们如何关联、哪些计算可以复用 | `loyalty_v3` 是权威的会员表；`revenue = price * qty - refunds` | `janus context build`、手动编辑、智能体提议的变更 |
| **`knowledge/rules/`** | Schema 无法承载的业务规则和运营策略 | "active customer 排除服务账号"；"始终过滤 `is_deleted = false`" | 手动编辑或智能体提议的变更 |
| **`knowledge/sql/`** | 经过确认的自然语言到 SQL 配对，每个配对一个 markdown 文件，是召回的事实来源 | "按收入排名的头部客户" → 已采纳的 SQL | `janus memory store`、手动编辑 |
| **记忆索引**（`.janus/memory/`） | 基于 MDL + `knowledge/` 的派生检索索引（可选 LanceDB，否则为 grep） | 可随时重建，已加入 gitignore | `janus memory index` |

MDL 说明数据*意味着什么*，`knowledge/rules/` 说明团队希望它*如何被使用*，`knowledge/sql/` 记录什么*有效*。前三者是你仓库中受版本控制的文件；记忆索引则是根据它们重建的派生产物。它们共同构成其他文档所指的上下文层，参见[Janus AI 所说的上下文是什么？](/oss/concepts/what_is_context)。

智能体在为新问题收集上下文时，会从所有这些位置读取。MDL 和规则很少变动；自然语言到 SQL 配对会随使用而增长，索引则根据它们重建。

## 为什么这些知识值得信赖

- **可审阅。** 每一个定义、规则和示例都是你可以在拉取请求（PR）中阅读的文件。没有由黑盒嵌入来决定你的指标含义。
- **有版本且对 Git 友好。** 知识与你的代码一同演进，拥有完整的历史记录，并可以分叉、比对和回滚。
- **有证据可追溯。** 丰富化过程会记录某个映射*为何*成立（来源文档或列），因此在业务变化时可以重新验证。
- **持续累积。** 每一个经过确认的答案都可以输入记忆，使下一个问题以及下一个仪表盘从更靠前的位置开始。

## 查询工作流的实际运行

`usage` 指南编排了日常的使用模式：

```text
User asks a business question
  │
  ├── 1. janus memory recall   → find similar accepted NL-SQL pairs
  ├── 2. janus memory fetch    → retrieve relevant models, columns, relationships
  ├── 3. Write SQL against MDL objects, not raw tables
  ├── 4. janus dry-plan        → see expanded SQL before execution
  ├── 5. janus --sql ...       → execute
  ├── 6. Repair on failure    → diagnose at MDL layer vs DB layer
  └── 7. janus memory store    → persist the confirmed pair
```

每一步都是智能体编排的确定性原语。推理过程在智能体的推理中清晰可见，而不是埋在封闭的产品之中。

## 这与"更多示例"有何不同

把更多示例塞进提示词有其上限：模型看到 Schema，然后尽力而为。

Janus AI 则让系统能够持续累积：

- 反复出现的问题每次都能检索到更好的示例。
- 反复出现的指标会复用已采纳的 SQL 模式。
- 随着项目增长，Schema 检索会越来越精准。
- 纠正会成为未来的依据，而不是在会话结束时消失。
- 团队可以提交 `knowledge/sql/`，使新环境继承已有的学习成果。

智能体本身并没有变得更聪明，而是它所读取的上下文层变得更丰富了，并且每一步都可以审阅。

## 另请参阅

- [记忆如何随时间变得更智能？](./memory_system.md)：召回与索引的机制。
- [MDL 对智能体有什么作用？](./what_is_mdl.md)：智能体所读取的语义契约。
- [优化回答质量](/oss/guides/refine)：运行丰富化闭环的操作指南。

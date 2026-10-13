# 记忆系统

记忆是 Janus AI 上下文系统中的行为层。

MDL 告诉智能体你的数据意味着什么，指令告诉它团队希望如何使用这些数据，而记忆告诉它过去什么做法有效：哪些 Schema 项相关、哪些 SQL 回答过类似的问题，以及团队已经确认过哪些示例。

没有记忆，每个问题都从零开始。有了记忆，每个被采纳的答案都可以让下一个答案，以及下一个仪表盘，更容易找到依据。它是[学习闭环](/oss/concepts/agent_learning)中的检索部分：闭环负责把知识记录下来，记忆则在类似的问题出现时把它找回来。

## 为什么记忆很重要

业务问题总是以细微的变化重复出现：

- "本月按收入排名的头部客户"
- "本季度按 ARR 排名的头部账户"
- "按客户细分统计的收入，不含退款"
- "月活跃用户，但仅限付费工作区"

智能体不应该每次都重新发现相同的关联、过滤条件和指标定义。它应当能够检索上下文层中的相关部分，并复用经过验证的示例。

这正是 Janus AI 记忆所提供的能力。

## 记忆存储什么

**事实来源是项目中的 markdown 文件**：经过确认的自然语言到 SQL 的配对存放在 `knowledge/sql/*.md` 中，业务规则存放在 `knowledge/rules/` 中。这些都是普通文件，你可以像对待其他源代码一样提交和审阅。

在这些 markdown 之上，Janus 会构建一个用于检索的**派生索引**。安装可选的 `memory` extra 后，它是位于 `.janus/memory/` 下的 [LanceDB](https://lancedb.com/) 嵌入索引（已加入 gitignore，可随时重建）；未安装时，无依赖的 grep 后端会直接搜索 markdown。无论哪种方式，索引都是可以随时丢弃的，`knowledge/` 才是持久化的一层。

索引涵盖两类内容：

| 内容 | 来源 | 为什么重要 |
| --- | --- | --- |
| Schema 项：模型、列、关系、视图、Cube、业务规则 | MDL + `knowledge/rules/` | 让智能体为某个问题检索正确的上下文，而无需把整个项目塞进提示词。 |
| 自然语言到 SQL 的配对 | `knowledge/sql/*.md` | 为智能体提供来自你真实业务的少样本示例，而不是通用示例。 |

## 有无 `memory` extra 的区别

无论如何，事实来源都是相同的，区别只在于检索引擎：

| | 使用 `memory` extra（LanceDB） | 不使用（grep，默认） |
| --- | --- | --- |
| NL→SQL `recall` | **语义检索**：基于嵌入相似度，因此改写的问法也能匹配（存入"月度收入"，可以召回"每月销售额"） | **词法检索**：对 `knowledge/sql/*.md` 做词元重叠与子串匹配，在查询时直接读取。没有共同词语的改写问法无法匹配 |
| 持久化索引 | 位于 `.janus/memory/` 下的 LanceDB（由 `index`/`store` 构建） | 无，markdown 本身就是索引，因此 `index` 为空操作 |
| Schema 搜索（`fetch`） | 可用（对 Schema 项进行嵌入检索） | **不可用**，需要嵌入；大型 Schema 应安装该 extra |

grep 后端是零依赖的回退方案，开箱即用，并保留 `store`/`recall` 功能，但召回质量较低。安装该 extra（或设置 `JANUS_MEMORY_BACKEND=lancedb`）即可启用语义召回和 Schema 搜索；切换时 `knowledge/` 中的文件不会有任何变化。

## 记忆如何被使用

当智能体通过 Janus AI 回答问题时，记忆通常会在编写 SQL 之前参与其中：

```text
User question
  |
  |-- janus memory recall -q "..."  -> find similar accepted questions and SQL
  |-- janus memory fetch -q "..."   -> find relevant models, columns, relationships, and instructions
  |-- Agent writes SQL against MDL objects
  |-- Janus AI plans and executes the query
  |-- janus memory store            -> save confirmed NL-SQL pair
```

这个循环为智能体提供两类依据：

- **相关上下文**：模型和指令中与当前问题相关的部分。
- **已验证的行为**：类似问题过去是如何被回答的示例。

## 记忆不能替代 MDL

记忆不定义你的语义，MDL 才定义。

记忆帮助智能体找到并复用上下文，但持久的契约仍然存在于项目文件中：模型、关系、视图、Cube 以及 `knowledge/`。如果某个定义重要到需要约束未来的行为，就把它放进 MDL 或 `knowledge/rules/`，然后重新为记忆建立索引。

可以把记忆看作建立在契约之上的检索与学习层。

## 随时间改进的部分

传统的 text-to-SQL 提示词有固定的上限：模型看到 Schema，然后尽力而为。记忆突破了这一上限：每个被采纳的答案都会成为可检索的示例，随着项目增长，Schema 检索会变得越来越精准，而纠正也会被保留下来，而不是随着聊天会话结束而消失。完整的累积闭环，以及每个产物在其中所处的位置，请参见[智能体如何从你的上下文中学习？](/oss/concepts/agent_learning)。

目标不是记住每一个答案，而是让智能体在推理之前更擅长找到正确的上下文。

## 何时重新索引

`janus memory store` 会把经过确认的 NL→SQL 配对写入 `knowledge/sql/` 并为其建立索引。索引中 Schema 和规则的部分则通过以下命令重建：

```bash
janus memory index
```

以下情况之后需要重新索引：

- 编辑模型描述、列、关系、视图或 Cube
- 修改 `knowledge/rules/`
- 添加或编辑 `knowledge/sql/` 中的配对
- 完成一次大规模的上下文丰富工作

命令详情请参见[优化回答质量](/oss/guides/refine)指南和 [CLI 参考](/oss/reference/cli#janus-memory--schema--query-memory)。

## 共享记忆

共享记忆就是提交 `knowledge/`。`knowledge/sql/*.md` 中的 NL→SQL 配对是普通、可审阅的文件，提交之后，每个环境都会获取它们；下一次执行 `janus memory index` 时，本地索引会根据这些文件重建。位于 `.janus/memory/` 下的派生索引仍保持在 gitignore 之中，因为它可以从 markdown 重新生成，不属于协作的载体。

（如果你有一个旧项目，其历史仍保存在 LanceDB 索引中？`janus memory export` 会将其导出到 `knowledge/sql/*.md`，参见[迁移](/oss/reference/migration)。）

## 简而言之

- **MDL** 定义业务含义。
- **`knowledge/`** 记录业务规则和经过确认的自然语言到 SQL 配对，可提交且可审阅。
- **记忆** 是派生索引，用于检索相关上下文并召回已验证的示例。

记忆使 Janus AI 能够随使用而改进，同时保证事实来源可检查、可版本化。

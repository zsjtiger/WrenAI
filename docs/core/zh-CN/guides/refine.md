---
sidebar_label: 优化回答质量
---

# 优化回答质量

脚手架只会给你一个基础 MDL。本指南介绍如何闭合这个循环：引入数据库之外的业务含义，保存经过验证的示例，并让智能体从每一个已确认的回答中持续积累经验。它是[学习闭环](/oss/concepts/agent_learning)的动手实践部分：这里的知识越丰富，下游的 BI 就越可信。

## 完成后你会得到

- `knowledge/rules/` 下的业务规则，记录标准表和团队约定
- `knowledge/sql/` 下经过确认的自然语言到 SQL 配对，并提交到你的仓库
- 基于 MDL 与 `knowledge/` 的记忆索引，使智能体能为每个问题检索相关上下文
- 一个每当有人确认回答，就对你的业务更加熟悉的智能体

## 可选：`memory` 额外依赖

优化开箱即用：`janus memory store`、`index` 和 `recall` 直接作用于 `knowledge/` 中的 markdown，无需额外依赖（基于 token 或子串匹配）。

只有当你需要**语义**（embedding）召回和 Schema 搜索（`janus memory fetch`）时，才需要安装 `memory` 额外依赖：

```bash
pip install "janusai[memory]"
# combine with your data source extra as needed:
pip install "janusai[memory,postgres]"
```

安装该额外依赖后，召回基于 embedding，并由 LanceDB 缓存索引；未安装时，相同的命令会回退到无依赖的 grep 后端。

## 当前流程

日常的优化循环依赖 `usage` 指南，以及若干 `janus memory` 命令和 `knowledge/rules/` 中的编辑。当你需要比增量编辑更深入的工作时，例如跨整个项目回填枚举含义、单位、默认过滤条件、同义词或命名指标，请使用下文介绍的 [`enrich-context`](#enrich-context) 指南。

### 1. 在 `knowledge/rules/` 中记录业务规则

`knowledge/rules/` 用于记录那些无法从 Schema 中看出的规则。每个主题使用一个 markdown 文件（例如 `knowledge/rules/revenue.md`）：

```markdown
## Business rules
- Revenue queries must use `net_revenue`, not `gross_revenue`.
- All active-customer queries exclude rows where `is_internal = true`.

## Canonical tables
- Use `customers` for analytics, not `customers_v3` or `loyalty_v3`.

## Formatting
- Currency is USD; display with thousand separators and 2 decimals.
- Timestamps are stored in UTC.
```

每个文件（以及其中的每个 `##` 标题）都会成为记忆中可检索的一个片段。你可以手动编辑，也可以在智能体发现反复出现的混淆时，让它提出修改建议。（旧项目：根目录下的 `instructions.md` 仍会被读取，但已被弃用，请将其移入 `knowledge/rules/`；参见[迁移](/oss/reference/migration)。）

### 2. 让 `usage` 从每个已确认回答中积累经验

日常使用的 `usage` 指南会自动保存已确认的回答：

```text
User asks a question
  → janus memory recall  (find similar past pairs)
  → janus memory fetch   (retrieve relevant schema)
  → write SQL, dry-plan, execute
  → janus memory store   (write the confirmed pair to knowledge/sql/ + index)
```

每次 `store` 都会写入一个 `knowledge/sql/<slug>.md` 文件——该 markdown 即为持久化记录，索引由它构建而来。未来遇到类似问题时，回答会更快、更准确，无需单独的补充阶段。

### 3. 每次变更后重新建立索引

每当你编辑 MDL 或 `knowledge/`，请重建记忆索引，使智能体的检索反映最新上下文：

```bash
janus memory index
```

这会把 MDL、`knowledge/rules/` 和 `knowledge/sql/` 重新读入索引。定向检索（`janus memory fetch -q "..."`）和召回（`janus memory recall -q "..."`）现在即可看到新上下文。运行 `janus memory check` 可查看索引是否与 markdown 保持同步。

### 4. 提交学到的上下文

这些配对本身就是文件——提交 `knowledge/` 即是导出：

```bash
git add knowledge/
git commit -m "curate query pairs and rules from this sprint"
```

新环境会在下一次 `janus memory index` 时自动获取它们（该命令会根据已提交的 markdown 重建本地索引）。

## 何时需要回到这里

- 用户抱怨智能体选错了表
- 出现新的业务术语（项目名称、指标、客户分群）
- 你导入了新数据集，需要教会智能体它的特殊之处
- 你希望团队成员的环境继承已积累的经验

## 记忆维护

由于配对以文件形式存放在 `knowledge/sql/` 下，维护工作主要就是普通的文件编辑：

| 操作 | 方法 |
|---|---|
| 浏览已保存的配对 | `janus memory list`，或阅读 `knowledge/sql/*.md` |
| 修正错误的配对 | 编辑（或删除）其 `knowledge/sql/<slug>.md`，然后运行 `janus memory index` |
| 共享已确认的配对 | 提交 `knowledge/sql/`（无需导出步骤） |
| 检查索引与 markdown 是否一致 | `janus memory check` |

完整的记忆命令列表，请参见 [CLI 参考](/oss/reference/cli)。

## `enrich-context`

`enrich-context` 指南比增量编辑 `knowledge/rules/` 更深入。它会读取你放入 `<project>/raw/` 的所有内容（PDF、术语表、手册、分析师 SQL、数据字典），与当前的 MDL 和 `knowledge/` 进行比对，并填补缺口，且只写回可供审阅、受版本控制的产物。它依据一份包含十类缺口的目录工作：枚举值含义、单位、NULL 语义、魔术哨兵值、默认过滤条件、同义词、时间约定、跨系统标识符、货币规则，以及标准表偏好。命名的聚合指标（ARR、流失率、DAU）会被提议为 Cube。

在会话开始时选择以下两种模式之一：

- **问答模式（Grill mode）**：智能体每次只提出一个问题，逐一走查每个缺口，提出有针对性的问题（"`customers`、`customers_v3`、`loyalty_v3` 中哪一个是标准表？"、"`status = 4` 是什么意思？"）。你用平实的语言回答，智能体会根据回答的类别起草修改，并修补 MDL 或 `knowledge/`（规则和自然语言到 SQL 的配对）。经你同意后，它还可以从实时数据库中抽样低基数列，以发现枚举值和哨兵值。
- **自动驾驶模式（Auto-pilot mode）**：将文档、术语表、SQL 历史或指标手册放入 `<project>/raw/`，智能体会阅读它们、直接应用其最佳推断，并且只在原始内容与 MDL 冲突，以及高影响范围的新增内容（新的 Cube / 视图 / 关系）时，才升级为问答模式。最后它会给出一份带置信度标记的审计报告。

两种模式都只会**新增**内容。它们从不修改已有字段；矛盾之处会列在"请手动修复"清单上。安装了 `janus` 技能（`npx skills add CrossNow/JanusAI`）后，只需说"enrich context"或"grill me on this project"即可触发。该存根会通过 `janus skills get enrich-context` 获取指南。完整说明参见[技能参考](/oss/reference/skills#enrich-context)。

## 另请参阅

- [智能体如何从你的上下文中学习？](/oss/concepts/agent_learning)：这一循环背后的设计理念
- [记忆如何随时间变得更智能？](/oss/concepts/memory_system)：索引了哪些内容，以及召回如何工作
- [为你的业务建模](./model.md)：开始优化之前的脚手架步骤

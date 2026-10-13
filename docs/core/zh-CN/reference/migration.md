---
sidebar_label: 迁移
---

# 迁移

当项目布局的 `schema_version` 发生变化时，如何把现有项目升级到新版本。每次迁移都只向前进行、幂等且不具破坏性：在你验证结果之前，现有文件都会保留在原位。运行 `janus context upgrade` 即可升级到最新版本；下面每个版本的说明涵盖了自动重新标记（restamp）之外需要额外处理的内容。

## 迁移到 schema 版本 5

版本 5 保留了按文件夹组织的 MDL 布局，并新增了 **`knowledge/`**，作为业务规则和 NL→SQL 问答对的一等公民存放位置。这些内容以前分别存放在 `instructions.md`、`queries.yml` 和 LanceDB 记忆索引中。

> 通过 `janus context init` 新建的项目已经是 v5，以下步骤只适用于 v5 之前创建的项目。

### 1. 升级布局

```bash
janus context upgrade --dry-run   # 预览将创建或修改的文件
janus context upgrade             # 重新标记为 schema_version 5，并创建 knowledge/
```

对于 v2 至 v4 的项目，这会把 `schema_version` 升级到 5，并创建 `knowledge/` 骨架（`rules/`、`glossary/`、`metrics/`、`caveats/`、`sql/` 以及 `knowledge.yml`）；v1 项目也会在此过程中被重组为按文件夹组织的布局。

### 2. 把业务规则迁移到 `knowledge/rules/`

`instructions.md` 仍然可以使用：`janus context build` 和 `janus memory index` 会与 `knowledge/rules/*.md` 一起读取它，但它已**弃用**，并会输出提示。请把其中的内容移动到 `knowledge/rules/` 下（可以按主题拆分）：

```bash
mv instructions.md knowledge/rules/general.md
```

### 3. 把语义记忆迁移为 Markdown

在 v5 中，`knowledge/sql/` 下的 Markdown 文件是 NL→SQL 问答对的**事实来源**；LanceDB 索引则成为由它们重建的派生产物（就像 `target/mdl.json` 由你的 YAML 重建一样）。

如果你在 `~/.janus/memory` 中已有 LanceDB 记忆，请先导出（读取 LanceDB 需要 `memory` 扩展）：

```bash
janus memory export                 # query_history → knowledge/sql/*.md
janus memory index                  # 从 knowledge/sql/ 重建派生索引
janus memory recall -q "revenue"    # 验证召回是否仍然正常
janus memory reset                  # 验证通过后执行 — 只会删除派生索引
```

`export` 会保留每个问答对的来源和时间戳，按问题去重，并且**从不删除 LanceDB**：验证之后需要你自己执行 reset。自动生成的种子问答对会被跳过（它们会在 `index` 时重新生成）；如果要保留它们，请传入 `--include-seed`。在过渡期间，`index` 仍会加载 `queries.yml`，但 `janus memory store` 新增的问答对现在会写入 `knowledge/sql/`。

`store`、`index` 和 `recall` 在**没有** `janus[memory]` 的情况下也能工作：问答对直接写入 `knowledge/sql/` 并在其中搜索。只有需要语义（嵌入）召回和 Schema 搜索时，才需要安装 `janus[memory]`。参见 [CLI 参考](./cli.md#janus-memory--schema--query-memory)。

迁移完成后，项目是自包含且对 Git 友好的：MDL、`knowledge/` 以及（在 SaaS 上）`policy/` 都存放在一起，而且记忆索引可以从已提交的 Markdown 重新生成。完整的布局参见 [MDL Schema 参考](./mdl.md)。

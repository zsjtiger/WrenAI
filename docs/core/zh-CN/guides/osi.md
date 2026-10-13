---
sidebar_label: OSI（开放语义互换）
---

# 从 OSI 语义模型构建 MDL

[开放语义互换](https://github.com/open-semantic-interchange/OSI)（Open Semantic Interchange，OSI）是一项与厂商无关的语义模型规范，由 Snowflake、Salesforce、dbt Labs、Databricks、Cube、AtScale 等公司共同支持。如果你的团队已经将某一份 OSI YAML 发布为分析定义的唯一事实来源，Janus 可以直接读取它并构建 `target/mdl.json`，无需将模型分叉为一个平行的 janus 项目。

```bash
janus context build --from-osi semantic_model.yaml --data-source postgres
# → ./target/mdl.json
```

## OSI 项目与 janus 项目

| | Janus 项目（原生） | OSI 项目，保留为源 | OSI 项目，一次性迁移 |
|---|---|---|---|
| **源文件** | `janus_project.yml` + `models/<name>/metadata.yml` + `views/` + `relationships.yml` | 单个 `*.yaml` OSI 文件 | 迁移后：janus 项目布局 |
| **作者** | 你（或 `generate-mdl` 智能体指南） | OSI 工具 / 厂商 / 外部团队 | `init` 之后由你接管 |
| **Janus 命令** | `janus context init` → 编辑 → `build` | `janus context build --from-osi <file>` | `janus context init --from-osi <file>` → 编辑 → `build` |
| **能否在 Janus 内编辑？** | 可以，这正是重点 | 不能，Janus 按原样读取该文件 | 迁移后可以 |
| **Janus 专属提示存放位置** | 每个模型的 YAML | OSI 的 `custom_extensions[vendor_name=JANUS]` 块 | 每个模型的 YAML（迁移时从 OSI 提取） |
| **是否与 OSI 保持同步？** | 不适用 | 是，每次构建都会重新读取 OSI | 否，单向快照 |

有三种情况可以选择：

- **你从第一天起就拥有这份语义模型** → 使用原生 janus 项目流程。
- **OSI 文件与其他工具共享（Snowflake Cortex、Salesforce、Cube 等），而你希望 Janus 成为众多消费者之一，且不产生分叉** → 使用 `janus context build --from-osi`。每次构建都会重新读取 OSI 文件。
- **你从 OSI 文件起步，但现在希望在 Janus 内完全掌控（Cube、视图、RLAC、OSI 未建模的自定义计算）** → 使用 `janus context init --from-osi` 一次性迁移，然后直接编辑生成的 YAML。参见[迁移为原生 janus 项目](#migrate-to-a-native-janus-project)。

三条路径生成的 `target/mdl.json` 结构完全相同，Janus 并不关心你是如何得到它的。

## 快速开始

假设你有如下 OSI 文件（节选自 TPC-DS 零售示例）：

```yaml
# semantic_model.yaml
version: "0.2.0"
semantic_model:
  - name: tpcds_retail
    ai_context:
      instructions: "Retail analytics. Revenue is in USD."
    datasets:
      - name: store_sales
        source: tpcds.public.store_sales
        primary_key: [ss_item_sk, ss_ticket_number]
        fields:
          - name: ss_item_sk
            expression: ss_item_sk
          - name: ss_ext_sales_price
            expression: ss_ext_sales_price
      - name: customer
        source: tpcds.public.customer
        primary_key: [c_customer_sk]
        fields:
          - name: c_customer_sk
            expression: c_customer_sk
          - name: full_name
            expression:
              dialects:
                - dialect: ANSI_SQL
                  expression: c_first_name || ' ' || c_last_name
    relationships:
      - name: sales_to_customer
        from: store_sales
        to: customer
        from_columns: [ss_item_sk]
        to_columns: [c_customer_sk]
```

运行：

```bash
janus context build --from-osi semantic_model.yaml --data-source postgres
```

Janus 会读取该文件，将每个 dataset 转换为一个模型，合成关联的 join 条件，把 OSI 的 `ai_context.instructions` 打包进 manifest，并写入 `./target/mdl.json`，之后即可用于 `janus --sql` 或任何智能体技能。

你还会看到一些警告，告诉你理想的 manifest 还缺少什么，参见下方的[何时需要 `JANUS` 块](#what-needs-a-janus-block)。

## `JANUS` 扩展块

OSI 没有针对扩展的文件系统约定。它唯一认可的扩展机制是文档内的 `custom_extensions: [{vendor_name, data}]` 字段，该字段存在于文档的每一层级中。Janus 只读取 `vendor_name: JANUS` 条目，其余全部忽略。

OSI 文档根部的典型扩展块：

```yaml
custom_extensions:
  - vendor_name: JANUS
    data: |
      {
        "dialect": "SNOWFLAKE",
        "metrics": "note"
      }
```

按 dataset 覆盖的设置（用于 OSI 无法表达的内容，最重要的是列类型）：

```yaml
datasets:
  - name: store_sales
    source: tpcds.public.store_sales
    custom_extensions:
      - vendor_name: JANUS
        data: |
          {
            "column_types": {
              "ss_sold_date_sk": "DATE",
              "ss_ext_sales_price": "DECIMAL(18,2)",
              "ss_quantity": "INTEGER"
            },
            "primary_key": "ss_ticket_number"
          }
    fields:
      - name: amount_eur
        expression: { dialects: [{dialect: ANSI_SQL, expression: amount * 0.92}] }
        custom_extensions:
          - vendor_name: JANUS
            data: '{"type": "DECIMAL(18,2)", "not_null": true}'
```

按规范，`data` 字段是一个 JSON 字符串。对于手写文件，Janus 也接受原始的 YAML 字典。

### 支持的键

| 键 | 作用域 | 效果 |
|---|---|---|
| `dialect` | 根、semantic_model | 从 `expression.dialects[]` 中提取哪一种 OSI 方言。默认为 `ANSI_SQL`，对 `snowflake` / `databricks` 数据源会自动推断。 |
| `metrics` | 根、semantic_model | 如何处理 OSI 顶层的 `metrics`：`note`（默认，作为 instructions 追加）或 `skip`。 |
| `default_semantic_model` | 根 | 当文件包含多个 `semantic_model[]` 条目时，构建哪一个。 |
| `column_types` | semantic_model：`{dataset: {field: type}}`<br/>dataset：`{field: type}` | 列类型。OSI 没有原生的类型系统。 |
| `primary_key` | semantic_model：`{dataset: column}`<br/>dataset：`column` | 当 OSI 定义了复合主键时，选取其中一列。 |
| `type`、`not_null` | field | 按字段覆盖。 |

## 优先级

解析顺序，从高到低：

1. CLI 标志（`--data-source`、`--semantic-model`、`--dialect` 等）
2. `semantic_model[i].custom_extensions[vendor_name=JANUS]`
3. 文档根部的 `custom_extensions[vendor_name=JANUS]`
4. Dataset / field 的 `custom_extensions[vendor_name=JANUS]`（仅适用于按 dataset / 按字段的键）
5. 内置默认值

根部与 semantic_model 两级支持，意味着你可以一次性写好全局默认值，只需在确实需要不同设置的个别 `semantic_model` 条目上添加覆盖项，例如文件中包含多个语义模型时。

## 映射概览

| OSI | Janus MDL |
|---|---|
| `dataset.source: a.b.c` | `model.table_reference: {catalog: a, schema: b, table: c}` |
| `dataset.source` 包含 `SELECT`/`FROM`/换行 | `model.ref_sql` |
| `dataset.fields[*].name` + `expression` | `model.columns[]`：由方言选取表达式，类型来自 JANUS 块或 `is_time` 提示 |
| `dataset.primary_key: [x]` | `model.primary_key: x`（复合数组会发出警告，并取第一列，除非被覆盖） |
| `relationships[]`（OSI 中始终为多对一） | 带有合成 `condition` 和 `MANY_TO_ONE` 的 janus `relationships` |
| `field.dimension.is_time: true` | `column.type: TIMESTAMP`（没有显式类型覆盖时） |
| `semantic_model.ai_context.instructions` | MDL `_instructions` |
| `metrics[]`（OSI 顶层） | 渲染为 markdown 注释，并追加到 instructions |
| `unique_keys` | _不转换_，Janus 没有对应概念 |
| 其他厂商的 `custom_extensions` | _忽略_ |

## 何时需要 `JANUS` 块 {#what-needs-a-janus-block}

对于以下每种情况，`validate --from-osi` 都会输出一段**可直接复制粘贴的 YAML 片段**，你可以把它粘贴进你的 OSI 文件。

### 未定义类型的字段

OSI 不携带列类型。若没有 `JANUS` 覆盖，每个字段都默认为 `VARCHAR`（若 `dimension.is_time: true` 则为 `TIMESTAMP`）。`validate` 会按 dataset 输出如下提示：

```text
[WARNING] dataset 'store_sales': 8 field(s) have no type — defaulted to VARCHAR.
  Add to dataset 'store_sales' in the OSI file:

    custom_extensions:
      - vendor_name: JANUS
        data: |
          {
            "column_types": {
              "ss_sold_date_sk": "DATE",
              "ss_ext_sales_price": "DECIMAL(18,2)",
              ...
            }
          }
```

### 复合主键

OSI 允许 `primary_key: [col_a, col_b]`，而 Janus MDL 只接受一列。Janus 会选取第一列，并输出一段片段，便于你覆盖：

```text
[WARNING] dataset 'store_sales': composite primary_key
  ['ss_item_sk', 'ss_ticket_number'] — Janus MDL takes one column.
  Janus picked 'ss_item_sk'. To override, add to dataset 'store_sales':

    custom_extensions:
      - vendor_name: JANUS
        data: '{"primary_key": "<one of: ss_item_sk, ss_ticket_number>"}'
```

### 跨 dataset 指标

Janus Cube 绑定到单一的基础对象，因此跨多个 dataset 聚合的 OSI 顶层指标无法成为一等公民的 Cube。它们会被渲染为追加到 `instructions` 的 markdown 注释，供 LLM 使用，但不会成为可查询的度量：

```text
[WARNING] metric 'customer_lifetime_value': expression references 2 datasets
  (customer, store_sales) — emitted as instruction note only.
```

引用单个 dataset 的指标默认也会得到同样的处理（`metrics: note`）。若要完全丢弃它们，请在 JANUS 块中设置 `metrics: skip`。

### 多个 `semantic_model` 条目

OSI 允许一个文件中包含多个 `semantic_model[]` 条目。Janus 每次调用只构建一个 MDL，因此存在歧义的文件会直接报错：

```text
[ERROR] OSI file has 2 semantic_models: model_a, model_b.
  Pass --semantic-model <name> or add at the OSI document root:

    custom_extensions:
      - vendor_name: JANUS
        data: '{"default_semantic_model": "<name>"}'
```

## CLI 命令

```bash
# Build (writes ./target/mdl.json by default)
janus context build --from-osi semantic_model.yaml --data-source postgres
janus context build --from-osi semantic_model.yaml --data-source snowflake \
  --output build/mdl.json

# Migrate to a native janus project (one-way)
janus context init --from-osi semantic_model.yaml --data-source postgres \
  --path my_project

# Validate — lints the conversion and prints actionable snippets
janus context validate --from-osi semantic_model.yaml --data-source postgres
janus context validate --from-osi semantic_model.yaml --data-source postgres --strict
janus context validate --from-osi semantic_model.yaml --data-source postgres --verbose

# Show — preview the resulting manifest without writing it
janus context show --from-osi semantic_model.yaml --data-source postgres
janus context show --from-osi semantic_model.yaml --data-source postgres --output json
janus context show --from-osi semantic_model.yaml --data-source postgres --output yaml
```

`--data-source` 是必填项，因为 OSI 有意不携带连接或方言的环境信息。如果文件包含多个模型，请将 `--from-osi` 与 `--semantic-model` 搭配使用。

## 迁移为原生 janus 项目 {#migrate-to-a-native-janus-project}

当 OSI 的表达能力不够用时，例如你需要 Cube、视图、RLAC/CLAC，或 OSI 未建模的计算列，请将 OSI 文件一次性转换为原生 janus 项目，然后直接编辑 YAML：

```bash
janus context init --from-osi semantic_model.yaml --data-source postgres --path my_project
```

这会复用与 `build --from-osi` 相同的转换器，然后生成标准的 janus 布局：

```text
my_project/
├── janus_project.yml          # name lifted from OSI semantic_model.name
├── models/
│   ├── customers/metadata.yml
│   └── orders/metadata.yml
├── relationships.yml
├── instructions.md           # OSI ai_context.instructions + metrics notes
└── AGENTS.md
```

迁移之后：

- OSI 文件**不再被引用**。你可以删除、归档，或保留以便比对，Janus 不会再读取它。
- 直接编辑生成的 YAML。在 `cubes/` 下添加 Cube，在 `views/` 下添加视图，在每个模型的 `properties` 下添加 RLAC，等等。
- 使用标准流程：`janus context validate` → `janus context build`。

OSI 转换通常会输出的任何警告（未定义类型的字段、复合主键、跨 dataset 指标）都会在 init 期间打印一次，以便你知道生成的 YAML 中哪些位置需要人工审核。

### 何时*不*迁移

如果你的 OSI 文件由上游团队更新，并且你希望 Janus 与之保持同步，**请勿**迁移，而应改用 `build --from-osi`。已迁移的项目是一个快照，之后的 OSI 编辑不会自动同步到 Janus，除非手动合并，或重新运行 `init --from-osi --force`（这会丢失你在迁移后所做的编辑）。

## 限制

- **不支持回写。** Janus 读取 OSI，但从不写回。对 OSI 文件的编辑需要在你的 OSI 工具中完成，Janus 会在下一次 `build` 时重新读取。
- **没有 Cube / 度量。** OSI 指标会映射为 instructions 注释，而不是 Janus Cube。如果你需要一等公民的 Cube，请改为在原生 janus 项目中建模。
- **没有视图。** OSI 没有视图概念，生成的 MDL 中 `views` 数组为空。
- **没有 `unique_keys`，也没有行级或列级访问控制。** OSI 0.2.x 未建模这些内容。如果你需要它们，可以在一个 sidecar janus 项目中编写，或等待即将发布的 OSI 规范版本。

对于 OSI 尚未覆盖的功能，建议的做法是：用 OSI 文件处理它擅长的部分（dataset、字段、关系、instructions），并在其上叠加一个小型的 janus 原生覆盖层来补齐缺口。目前这需要手动合并，两个来源之间没有自动合并。

## 另请参阅

- [OSI 规范](https://github.com/open-semantic-interchange/OSI/blob/main/core-spec/spec.md)：上游的 schema 和字段参考
- [管理项目](./manage_project.md)：原生 janus 项目流程
- [MDL 参考](/oss/reference/mdl)：转换另一端 Janus 产出的内容
- [连接你的数据库](./connect.md)：选择并绑定 profile

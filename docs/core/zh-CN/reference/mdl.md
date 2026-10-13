---
sidebar_label: MDL Schema
---

# MDL Schema 参考

本页说明 Janus 项目中的每一种 YAML 产物（`janus_project.yml`、模型、关联关系、视图、Cube 以及 `knowledge/` 文件）及其完整字段。

> 关于 MDL 的概念框架，参见[MDL 为智能体做了什么？](/oss/concepts/what_is_mdl)。项目生命周期命令参见[管理项目](/oss/guides/manage_project)。编辑后请运行 `janus context build`，完成标准的 YAML 编译流程。

## 项目结构

```text
my_project/
├── janus_project.yml               # 项目元数据
├── models/
│   ├── orders/
│   │   └── metadata.yml           # table_reference 模式（物理表）
│   ├── customers/
│   │   └── metadata.yml
│   └── revenue_summary/
│       ├── metadata.yml           # ref_sql 模式（由 SQL 定义的模型）
│       └── ref_sql.sql            # SQL 放在单独文件中（可选）
├── views/
│   ├── monthly_revenue/
│   │   ├── metadata.yml
│   │   └── sql.yml                # 语句放在单独文件中（可选）
│   └── top_customers/
│       └── metadata.yml           # 语句内联
├── cubes/
│   └── revenue/
│       └── metadata.yml
├── relationships.yml              # 所有关联关系
├── knowledge/                     # 业务上下文（schema_version 5+）
│   ├── rules/                     # 供智能体使用的业务规则（取代 instructions.md）
│   ├── glossary/  metrics/  caveats/
│   ├── sql/                       # NL→SQL 问答对：记忆的事实来源
│   └── knowledge.yml              # knowledge 维度的 schema_version（与 MDL 解耦）
├── instructions.md                # 已弃用：请迁移到 knowledge/rules/（仍会被读取）
├── queries.yml                    # 旧版 NL-SQL 问答对：已被 knowledge/sql/ 取代
├── .janus/                         # 运行时状态（被 gitignore）
│   └── memory/                    # 派生的 LanceDB 索引（可选；由 knowledge/sql/ 重建）
└── target/
    └── mdl.json                   # 构建产物（被 gitignore）
```

`janus_project.yml` 带有 `schema_version`；**版本 5** 是当前布局。要升级旧项目，并把 `instructions.md` 或记忆迁移到 `knowledge/`，请参见[迁移指南](/oss/reference/migration)（英文版）。

YAML 文件使用 **snake_case** 字段名。编译后的 `target/mdl.json` 使用 **camelCase**，这是引擎所要求的传输格式。

## `janus_project.yml`

```yaml
schema_version: 5
name: my_project
version: "1.0"
catalog: janus
schema: public
data_source: postgres
profile: my-pg
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 项目布局版本（当前为 `5`，新增一等公民的 `knowledge/`）。`2` = 每个实体一个文件夹，`3` = 支持 `dialect`，`4` = 复合主键，`5` = `knowledge/`。由 CLI 管理，使用 `janus context upgrade` 升级（参见[迁移指南](/oss/reference/migration)）。 |
| `name` | string | 是 | 项目标识符。 |
| `version` | string | 否 | 用户自定义的项目版本（自由格式，不影响解析）。 |
| `catalog` | string | 否 | **Janus AI 的命名空间**，不是你数据库的 catalog。默认为 `janus`。 |
| `schema` | string | 否 | **Janus AI 的命名空间**，不是你数据库的 schema。默认为 `public`。 |
| `data_source` | string | 否 | 数据源类型（`postgres`、`bigquery`、`snowflake` 等）。由 `janus context set-profile` 设置。 |
| `profile` | string | 否 | 已绑定的连接配置文件名称。由 `janus context set-profile` 设置。 |

> **`catalog` 和 `schema` 有两个层级。** 同样的字段名在两个位置有完全不同的含义。项目级字段是 Janus AI 的内部命名空间；模型级的 `table_reference.catalog` 和 `table_reference.schema` 则指向底层数据库中的位置。
>
> | 位置 | 指向 | 示例 |
> |---|---|---|
> | `janus_project.yml` → `catalog`、`schema` | Janus AI 命名空间 | `janus`、`public` |
> | `models/*/metadata.yml` → `table_reference.catalog`、`table_reference.schema` | 数据库位置 | `jaffle_shop`、`main` |

## 模型（`models/<name>/metadata.yml`）

每个模型在 `models/` 下有自己的目录。一个模型定义：

- 数据来源：`table_reference` 或 `ref_sql`
- 暴露哪些列
- 关联关系和计算字段

### 模型字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 唯一的模型名称（在 SQL 查询中使用）。 |
| `table_reference` | 二选一 | 映射到一张物理表（`catalog`、`schema`、`table`）。 |
| `ref_sql` | 二选一 | 作为模型数据源的 SQL SELECT。 |
| `columns` | 是 | 要暴露的列列表。 |
| `primary_key` | 否 | 唯一标识一行的列名；遍历 `TO_MANY` 关联时必填。 |
| `cached` | 否 | 查询结果是否缓存。默认为 `false`。 |
| `dialect` | 否 | 模型 `ref_sql` 的 SQL 方言。对该模型覆盖项目级的 `data_source`。需要 `schema_version: 3`。 |
| `properties` | 否 | 任意键值形式的元数据。 |

在同一个模型中同时使用 `table_reference` 和 `ref_sql` 会导致校验错误。

### `table_reference`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `catalog` | string | 否 | 数据源侧的 catalog（DuckDB 数据库名、BigQuery 项目、Snowflake 数据库）。没有 catalog 层的数据源可省略。 |
| `schema` | string | 否 | 数据源侧的 schema 或 dataset。扁平数据源可省略。 |
| `table` | string | 是 | 数据源侧的表或视图名称。 |

### 示例：`table_reference`

```yaml
name: customers
table_reference:
  catalog: jaffle_shop
  schema: main
  table: customers
primary_key: customer_id
columns:
  - name: customer_id
    type: INTEGER
    is_primary_key: true
    not_null: true
  - name: first_name
    type: VARCHAR
  - name: last_name
    type: VARCHAR
  - name: number_of_orders
    type: BIGINT
```

### 示例：`ref_sql`

```yaml
name: revenue_summary
ref_sql: |
  SELECT DATE_TRUNC('month', order_date) AS month,
         SUM(total) AS total_revenue
  FROM orders
  GROUP BY 1
columns:
  - name: month
    type: DATE
  - name: total_revenue
    type: DECIMAL
```

SQL 可以内联（如上），也可以放在同级的 `ref_sql.sql` 文件中。如果两者同时存在，以 `.sql` 文件为准。

### 列

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | SQL 中使用的列名。 |
| `type` | 是 | SQL 类型（`VARCHAR`、`INTEGER`、`DOUBLE`、`DATE`、`TIMESTAMP`、`BOOLEAN`、`DECIMAL`、`JSON` 等）。 |
| `is_calculated` | 否 | 若为 `true`，则该值在查询时由 `expression` 计算得出。 |
| `expression` | 否 | 计算列的 SQL 表达式，或用于简单重命名的单列引用。 |
| `relationship` | 否 | 关联关系的名称，使该列成为 join 句柄列。 |
| `not_null` | 否 | 约束提示。默认为 `false`。 |
| `is_primary_key` | 否 | 将该列标记为模型的主键。 |
| `is_hidden` | 否 | 引擎内部标志；该列会从符号表中移除，对所有客户端不可见。 |
| `properties` | 否 | 任意元数据（例如 `properties.description`）。 |

#### 计算列

```yaml
- name: total_with_tax
  type: DOUBLE
  is_calculated: true
  expression: "amount * 1.1"
```

#### 关联列

关联列声明通往另一个模型的 join 路径：

```yaml
- name: customer
  type: customers           # 相关模型的名称
  relationship: orders_customers
```

同一模型上的计算列可以遍历这个句柄：

```yaml
- name: customer_name
  type: VARCHAR
  is_calculated: true
  expression: "customer.first_name"    # 遍历 `customer` 句柄
```

> **目前还不支持在查询中直接遍历句柄。**
> `SELECT orders.customer.first_name FROM orders` 无法完成规划，会报错 `Schema error: No field named orders.customer.first_name`。原因是关联列被排除在模型注册到引擎的 Schema 之外：`Model::get_physical_columns` 只保留 `relationship` 未设置的列。问题跟踪见 [#2688](https://github.com/CrossNow/JanusAI/issues/2688)。

#### 通过 `expression` 重命名列

当 `is_calculated` 为 `false` 但存在 `expression` 时，该表达式必须是简单的列引用。引擎会从表达式中解析出物理列名，并使用模型中的列名作为别名：

```yaml
- name: customer_id        # 对外暴露的名称
  type: INTEGER
  expression: usr_id        # 物理列名
```

### 面向列级访问控制的选择性暴露

模型不必暴露底层表中的每一列。被省略的列对客户端物理上不可见：任何 SQL 都无法引用它们，它们也不会出现在 Schema 内省结果中。

这一点对 AI 智能体很重要：你从模型中省略的任何列，无论智能体如何请求，都无法通过 Janus AI 获取。

## 关联关系（`relationships.yml`）

```yaml
relationships:
  - name: orders_customers
    models:
      - orders
      - customers
    join_type: MANY_TO_ONE
    condition: orders.customer_id = customers.customer_id
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 唯一的关联关系标识符。 |
| `models` | array[string] | 是 | 恰好两个模型名称 `[from, to]`。 |
| `join_type` | enum | 是 | `ONE_TO_ONE`、`ONE_TO_MANY`、`MANY_TO_ONE` 或 `MANY_TO_MANY`。 |
| `condition` | string | 是 | SQL 等值条件，两侧都使用 `model.column` 引用。 |

`models` 中的第一个模型应出现在 `condition` 的左侧。只支持等值条件。

对于 `TO_MANY` 关联，遍历该关联的计算列必须使用聚合函数：引擎会把 join 包装在聚合子查询中，以防止行数膨胀。

## 视图（`views/<name>/metadata.yml`）

```yaml
name: top_customers
statement: |
  SELECT customer_id, SUM(total) AS lifetime_value
  FROM janus.public.orders
  GROUP BY 1
  ORDER BY 2 DESC
  LIMIT 100
properties:
  description: "Top customers by lifetime value"
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 唯一的视图名称。 |
| `statement` | string | 是 | 完整的 SQL SELECT。可以引用其他模型或视图。 |
| `dialect` | string | 否 | SQL 方言（仅作元数据；引擎使用通用解析器解析）。需要 `schema_version: 3`。 |
| `properties` | 否 | 任意元数据。 |

语句可以内联，也可以放在同级的 `sql.yml` 文件中。如果两者同时存在，以 `sql.yml` 为准。

视图不声明列：Schema 在查询时从语句中推断。视图可以引用其他视图；引擎会在解析模型之前递归展开它们。

## Cube（`cubes/<name>/metadata.yml`）

Cube 是预聚合的语义对象：一个基础模型或视图，加上声明好的度量、维度、时间维度和层级。

```yaml
name: revenue
base_object: orders
measures:
  - name: total
    expression: SUM(amount)
    type: DOUBLE
  - name: order_count
    expression: COUNT(*)
    type: BIGINT
dimensions:
  - name: status
    expression: status
    type: VARCHAR
time_dimensions:
  - name: order_date
    expression: order_date
    type: DATE
hierarchies:
  time: [order_date]
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 唯一的 Cube 名称。 |
| `base_object` | 是 | 该 Cube 聚合所基于的模型或视图。 |
| `measures[]` | 是 | 聚合值（`expression` + `type`）。 |
| `dimensions[]` | 否 | 分类型的分组维度。 |
| `time_dimensions[]` | 否 | 基于时间的分组维度。粒度在查询时通过 `--time-dimension name:granularity` 应用（参见 [CLI 参考](/oss/reference/cli#janus-cube--pre-aggregation-queries)）。 |
| `hierarchies` | 否 | 层级名称到有序维度或时间维度名称列表的映射，用于下钻。 |
| `refresh_time` | 否 | 缓存刷新间隔。 |
| `properties` | 否 | 任意元数据。 |

Cube 通过 `janus cube query` 以结构化方式查询，而不是手写 `GROUP BY` SQL。面向智能体的用法参见[使用 Cube 预聚合](/oss/guides/cubes)。

## 业务规则（`knowledge/rules/`）

面向 AI 智能体的自由格式 Markdown，包含业务和操作指导：`knowledge/rules/` 下每个主题一个文件。每个文件（以及其中每个 `##` 标题）都会成为记忆中可检索的片段。

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

规则由智能体使用，而不是由引擎使用，因此它们不会出现在 `target/mdl.json` 中。智能体通过以下方式访问它们：

- `janus context instructions`：获取完整文本，会话开始时运行一次
- `janus memory fetch -q "..."`：每个查询获取相关片段

> 顶层的 `instructions.md` 仍会被读取（与 `knowledge/rules/` 一起），但已**弃用**，请把它迁移到 `knowledge/rules/`。参见[迁移指南](/oss/reference/migration)（英文版）。

## NL→SQL 问答对（`knowledge/sql/`）

经过确认的自然语言到 SQL 的问答对，每对问答存为 `knowledge/sql/` 下的一个 Markdown 文件，是记忆召回的事实来源。文件包含 YAML frontmatter 和可选的正文：

```markdown
---
nl: monthly revenue by product category
sql: |
  SELECT category, DATE_TRUNC('month', order_date) AS month, SUM(amount)
  FROM orders
  GROUP BY 1, 2
source: user
datasource: postgres-prod
---
```

`janus memory store` 负责写入这些文件；`janus memory index` 会根据它们（重新）构建索引。顶层的旧版 `queries.yml` 在 `index` 时仍会自动加载，以便过渡，但新的问答对会写入 `knowledge/sql/`。参见[迁移指南](/oss/reference/migration)（英文版）。

## Snake_case 到 camelCase 的映射

`janus context build` 会把 YAML 字段名转换为 `target/mdl.json` 中的 camelCase：

| YAML | JSON |
|---|---|
| `table_reference` | `tableReference` |
| `ref_sql` | `refSql` |
| `is_calculated` | `isCalculated` |
| `not_null` | `notNull` |
| `is_primary_key` | `isPrimaryKey` |
| `primary_key` | `primaryKey` |
| `join_type` | `joinType` |
| `data_source` | `dataSource` |
| `layout_version` | `layoutVersion` |
| `refresh_time` | `refreshTime` |
| `base_object` | `baseObject` |

通用规则：以 `_` 切分，除第一个单词外每个单词首字母大写，然后拼接。其他所有字段（`name`、`type`、`catalog`、`schema`、`table`、`condition`、`models`、`columns`、`cached`、`dialect`、`properties`）在两种格式中完全相同。

`layoutVersion` 由 `janus context build` 根据项目的 `schema_version` 自动写入，你不需要在 YAML 中手动设置。

## 方言覆盖

模型和视图支持可选的 `dialect` 字段，用于声明其内嵌 SQL 使用的方言。需要 `schema_version: 3`。

| 设置 | 行为 |
|---|---|
| 省略 `dialect` | 回退到项目级的 `data_source`。默认行为。 |
| 设置 `dialect` | 引擎对该对象的 SQL 使用指定方言的解析器。 |

有效的方言值：`athena`、`bigquery`、`canner`、`clickhouse`、`databricks`、`datafusion`、`doris`、`duckdb`、`gcs_file`、`local_file`、`minio_file`、`mssql`、`mysql`、`oracle`、`postgres`、`redshift`、`s3_file`、`snowflake`、`spark`、`trino`。

### Schema 版本与布局版本

| `schema_version` | `layoutVersion` | 功能 |
|---|---|---|
| 1 | 1 | 旧版扁平文件项目格式。 |
| 2 | 1 | 每个实体一个文件夹的项目格式。 |
| 3 | 2 | 在模型和视图上新增 `dialect` 字段。 |
| 4 | 3 | 新增复合（列表形式）主键。 |
| 5 | 3 | 新增一等公民的 `knowledge/` 库。当前版本。 |

使用 `janus context upgrade` 升级版本。可以加上 `--dry-run` 先进行模拟运行。

## 推荐的 `.gitignore`

```text
target/
.janus/memory/
```

源 YAML 和 `knowledge/` 库（规则、术语表、指标、注意事项，以及 `knowledge/sql/` 下的 NL→SQL 问答对）都应提交。`target/mdl.json` 是派生产物；`.janus/memory/` 是由 `knowledge/sql/` 重建的二进制 LanceDB 索引，应提交 `knowledge/sql/*.md` 问答对，而不是索引。

## 另请参阅

- [管理项目](/oss/guides/manage_project)：生命周期命令、配置文件绑定、多环境工作流
- [CLI 参考](./cli.md)：每个 `janus` 命令
- [运维参考](/oss/reference/operational)（英文版）：所有路径、环境变量和发现规则
- [MDL 为智能体做了什么？](/oss/concepts/what_is_mdl)：概念框架

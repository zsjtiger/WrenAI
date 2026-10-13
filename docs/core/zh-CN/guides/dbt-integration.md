# dbt 集成

将 dbt 项目导入 Janus AI，即可通过 Janus 上下文层查询 dbt 模型。

## Janus 会导入哪些内容

dbt 本身已经包含智能体安全查询建模数据所需的上下文：模型和列的描述、refs、source 定义、测试元数据、编译后的 SQL、适配器 profile 设置，以及 `catalog.json` 中的物理列列表。Janus 会导入这些上下文，使智能体无需仅凭表名和列名，就去推断模型的用途、关联路径或可信约束。

Janus 将导入的 dbt 上下文存储在常规的 Janus 项目文件中：

| dbt 输入 | Janus 输出 | 重要原因 |
|-----------|-------------|----------------|
| 当前激活的 dbt target | Janus 连接 profile | 复用 dbt 使用的同一数据仓库连接目标 |
| 模型与 source 节点 | `models/*/metadata.yml` | 保留模型名称、表引用、描述、层级和列 |
| `relationships` 测试 | `relationships.yml` | 将经过测试的 dbt refs 转换为明确的 Janus 关联路径 |
| `not_null`、`unique`、`accepted_values` 测试 | 模型与列的元数据 | 为智能体提供经过验证的约束和有用的过滤值 |
| 测试结果 | `instructions.md` | 为智能体工作流呈现经过验证的约束和警告 |
| 模型图与元数据 | `queries.yml` | 为记忆提供感知 dbt 的示例问题和 SQL 种子 |

生成的 `janus_project.yml` 还会保留一个 `dbt` 绑定：

```yaml
dbt:
  project_dir: ../your-dbt-project
  profile: your_dbt_profile
  target: dev
```

`project_dir` 指向被导入的 dbt 项目，而 `profile` 和 `target` 记录导入时所使用的 dbt profile target。这使 Janus 项目可以追溯到其 dbt 源，并为后续工具提供足够的上下文，以便刷新或检查原始的 dbt 产物。

`dbt` 绑定只存储项目元数据。凭据保留在 Janus profile 以及这些 profile 引用的环境变量中。

## 前提条件

- 包含 `dbt_project.yml` 的 dbt 项目
- `~/.dbt/profiles.yml` 中的 dbt profile，或自定义的 `profiles.yml`
- 生成好的 dbt 产物：

```bash
cd your-dbt-project
dbt build
dbt docs generate
```

`dbt docs generate` 是必需的，因为 Janus 从 `target/catalog.json` 导入权威的列列表和类型。

## 导入 dbt Profile

将当前激活的 dbt target 转换为 Janus 连接 profile：

```bash
janus profile import dbt --project-dir ./your-dbt-project
```

常用选项：

| 标志 | 说明 |
|------|------|
| `--project-dir` | dbt 项目根目录。默认为 `.` |
| `--profiles-path` | dbt `profiles.yml` 的自定义路径 |
| `--profile` | 覆盖 dbt profile 名称 |
| `--target` | 覆盖 dbt target 名称 |
| `--name` | 目标 Janus profile 名称 |
| `--no-activate` | 保存 profile，但不将其激活 |

支持的适配器包括 `postgres`、`bigquery`、`snowflake`、`databricks`、`trino`、`clickhouse`、`duckdb`、`mysql`、`redshift`、`spark`、`athena`、`mssql` 和 `doris`。

## 导入 dbt 项目

从 dbt 产物生成 Janus 项目：

```bash
janus context import dbt \
  --project-dir ./your-dbt-project \
  --path ./janus-project
```

先预览生成的文件：

```bash
janus context import dbt \
  --project-dir ./your-dbt-project \
  --path ./janus-project \
  --dry-run
```

使用 `--force` 可覆盖由导入器管理的文件。

生成的文件：

| 文件 | 说明 |
|------|------|
| `janus_project.yml` | 项目元数据、数据源和 dbt 绑定 |
| `models/*/metadata.yml` | 导入的 dbt 模型和 source |
| `relationships.yml` | 从 dbt `relationships` 测试推断出的关联 |
| `instructions.md` | dbt 测试摘要、经过验证的约束和警告 |
| `AGENTS.md` | 智能体工作流指引 |
| `queries.yml` | 源自 dbt、用于记忆索引的种子自然语言 SQL 配对 |

导入器会跳过临时（ephemeral）模型、没有 catalog 列的节点，以及未出现在 `catalog.json` 中、仅存在于 manifest 的列。

## dbt 测试映射

Janus 将 dbt 测试导入为语义元数据：

| dbt 测试 | Janus 输出 |
|----------|-------------|
| `not_null` | 列上的 `not_null: true` |
| `unique` + `not_null` | `is_primary_key: true`，以及模型的 `primary_key` |
| `accepted_values` | `properties.accepted_values` |
| `relationships` | `relationships.yml` 中的一个条目 |

关联测试保留在 `relationships.yml` 中；导入器不会把关联的解引用信息写到外键列上。

## 构建与查询

编译 Janus 项目：

```bash
janus context build --path ./janus-project
```

对导入的模型名称运行 SQL：

```bash
janus --sql "SELECT * FROM fct_orders LIMIT 5"
```

## 记忆

如果已安装记忆功能，请为导入的项目建立索引：

```bash
janus memory index --path ./janus-project
```

记忆索引包含 dbt 描述、层级、测试状态、accepted values，以及来自 `queries.yml` 的种子配对。

## 完整 DuckDB 示例

```bash
cd jaffle_shop_duckdb
dbt build
dbt docs generate

janus profile import dbt --project-dir .
janus context import dbt --project-dir . --path ../janus-jaffle
janus context build --path ../janus-jaffle
janus --sql "SELECT * FROM fct_orders LIMIT 5"
```

## 故障排查

`dbt project file not found`：请确保 `--project-dir` 指向包含 `dbt_project.yml` 的目录。

`dbt manifest file not found`：运行 `dbt build` 或 `dbt compile`。

`dbt catalog file not found`：运行 `dbt docs generate`。

`Environment variable 'X' is required`：在导入之前，导出 dbt profile 中 `env_var()` 所引用的变量。

缺少列导致模型被跳过：使用 `dbt docs generate` 重新生成 `catalog.json`，然后重新运行 `janus context import dbt --force`。

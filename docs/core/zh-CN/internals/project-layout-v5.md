# Janus 项目布局（v5）

> **内部工程文档。** 位于 `docs/core/internals/`，不发布到文档站点。它描述 `schema_version: 5` 时 Janus 项目的磁盘结构，供贡献者在开发项目读写器（`core/janus/src/janus/context.py`）以及 CReport 应用工具（`core/janus/src/janus/creport/`）时参考。
>
> 关于每个 YAML 产物面向用户的字段清单，请参见 [MDL Schema 参考](../reference/mdl.md)。

Janus 项目是由 YAML/SQL 源文件加上少量生成产物组成的目录。v5 是当前布局：每个模型和视图各自一个文件夹，`cubes/` 作为预聚合的语义对象，一等公民的 `knowledge/` 知识库，以及作为生成前端的 CReport `apps/`。

## 版本轴

一个项目同时携带两个**相互独立**的版本号：

| 轴 | 文件 | 版本控制的内容 |
|------|------|------------------|
| `schema_version` | `janus_project.yml` | **项目布局形态**：文件路径、目录结构、必填字段 |
| `layoutVersion` | `target/mdl.json`（生成） | 编译后 manifest 的**引擎线格式** |

`schema_version` 是事实来源；`layoutVersion` 在构建时由它派生。

**v5 → `layoutVersion: 3`。** `schema_version 4`（复合主键）已经将引擎线格式迁移到 `layoutVersion 3`。v5 只新增了**不属于**编译后引擎 MDL 的磁盘项目内容（`knowledge/`、按文件夹划分的布局），因此复用 `layoutVersion 3`。`models` / `views` / `relationships` / `cubes` 编译后仍为相同的 JSON 结构。参见 `context.py` 中的 `_LAYOUT_VERSION_MAP`。

## 目录结构

```text
<project>/
├── janus_project.yml                # schema_version: 5 + name / catalog / schema / data_source
│
├── models/<name>/                  # MDL — one folder per model
│   ├── metadata.yml                #   columns, primary_key, table_reference, …
│   └── ref_sql.sql                 #   optional — SQL-defined model body (overrides inline ref_sql)
├── views/<name>/                   # MDL — one folder per view
│   ├── metadata.yml                #   view definition
│   └── sql.yml                     #   optional — statement in a separate file
├── relationships.yml               # MDL — all relationships
├── cubes/<name>/                   # MDL — pre-aggregated semantic objects
│   └── metadata.yml                #   base_object, measures, dimensions, time_dimensions, hierarchies
│
├── knowledge/                      # knowledge base (committed)
│   ├── rules/                      #   business rules (absorbs the legacy instructions.md)
│   ├── glossary/<term>.md
│   ├── metrics/
│   ├── caveats/
│   ├── sql/<slug>.md               #   NL→SQL pairs — source of truth for semantic memory
│   └── knowledge.yml               #   schema_version (knowledge axis — decoupled from MDL)
│
├── apps/<name>/                    # CReport apps — generated front-ends (see below)
│   ├── index.html                  #   entry point
│   ├── mdl.json                    #   compiled MDL copied into the app
│   └── *.parquet | *.duckdb        #   snapshot data assets (snapshot mode only)
│
├── instructions.md                 # business / operational guidance for agents (legacy; see knowledge/rules/)
├── AGENTS.md                       # agent guidance for this project
│
├── .janus/                          # runtime state (gitignored)
│   ├── apps.yml                    #   CReport app index — machine-written by `janus creport register`
│   └── memory/                     #   LanceDB semantic-memory index
└── target/
    └── mdl.json                    # build artifact (gitignored) — `janus context build` output
```

## MDL：`models/`、`views/`、`relationships.yml`、`cubes/`

这是数据模型。每个模型和视图都是一个包含 `metadata.yml` 的文件夹，并可选择附带一个侧边 SQL 文件（模型为 `ref_sql.sql`，视图为 `sql.yml`）。侧边文件存在时，优先于 `metadata.yml` 中的内联 SQL。关系统一存放在顶层的单个 `relationships.yml` 中。

`cubes/<name>/metadata.yml` 声明一个基于基础模型或视图的预聚合语义对象，包括其度量、维度、时间维度和层级。Cube 通过 `janus cube query` 以结构化方式查询。

以上四者都会通过 `janus context build` 编译为 `target/mdl.json`。读取器会根据 `schema_version` 进行分派：v1 使用扁平文件（`models/*.yml`、`views.yml`、`cubes/*.yml`）；v2 及之后的版本（包括 v5）使用上述按文件夹划分的布局。每个字段的说明参见 [MDL Schema 参考](../reference/mdl.md)。

## knowledge/

知识库承载数据库 Schema 无法表达的一切内容：业务规则（取代了较早的单文件 `instructions.md`）、术语表条目、命名指标、数据注意事项，以及 `sql/` 下的自然语言到 SQL 配对。后者是语义记忆的事实来源。知识库在 `knowledge.yml` 中拥有**自己的** `schema_version`，与 MDL 版本轴解耦，因为知识与数据模型的演进节奏不同。

## CReport 应用：`apps/` 与 `.janus/apps.yml`

`janus creport` 用于搭建、构建和部署从项目生成的小型前端应用。每个应用都是 `apps/<name>/` 下的一个独立文件夹：

- `index.html`：应用入口。
- `mdl.json`：应用所查询的编译后 MDL 副本。
- 快照数据资产（`*.parquet` / `*.duckdb`）：在**快照**数据模式下，数据随应用一同打包，并通过 wasm 在客户端查询。其他数据模式会查询实时数据源，不附带数据资产。

由于应用会发布到公开的静态托管平台，构建过程会校验每个 `apps/<name>/` 文件夹：入口文件存在、`mdl.json` 有效且非空、快照应用包含数据资产，并且不打包任何密钥。

应用**索引**位于 `.janus/apps.yml`。它是一个机器写入的注册表（状态机：`scaffolded → built → deployed`），其机制与 `~/.janus/profiles.yml` 索引连接 profile 的方式相同。该文件从不手动编辑，并且位于已加入 gitignore 的 `.janus/` 运行时目录中。

## 生成产物与已提交内容

| 路径 | 性质 |
|------|------|
| `models/`、`views/`、`relationships.yml`、`cubes/` | 已提交的 MDL 源文件 |
| `knowledge/` | 已提交的知识库 |
| `instructions.md`、`AGENTS.md` | 已提交的智能体指引 |
| `apps/<name>/` | 生成的前端（当你希望跟踪或部署时提交） |
| `.janus/`（`apps.yml`、`memory/`） | 运行时状态，已加入 gitignore |
| `target/mdl.json` | 构建产物，已加入 gitignore |

## 常量（`core/janus/src/janus/context.py`）

```python
_SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3, 4, 5}
_LATEST_SCHEMA_VERSION      = 5                       # = max(_SUPPORTED_SCHEMA_VERSIONS)
_LAYOUT_VERSION_MAP         = {1: 1, 2: 1, 3: 2, 4: 3, 5: 3}
```

完整的 v5 布局示例位于 [`examples/v5-jaffle/`](https://github.com/CrossNow/JanusAI/tree/main/examples/v5-jaffle)。

# 方案：认证定义、溯源、漂移检测与修正闭环

状态：P1–P5 已实现（见第 9 节）· 范围：`core/janus`（CLI、MCP、策略层）及 MDL 元数据约定

## 1. 背景与目标

Janus 目前能把数据库表接入语义层（MDL），并通过 CLI 和 MCP 提供查询。它还缺少四类能力，这些能力在 NVIDIA Auto Ontology 项目里有成熟的做法：

1. **认证定义**：区分哪些模型和指标经过人工确认，智能体应优先使用它们。
2. **溯源**：每个查询结果说明用到了哪些模型、Cube 和知识文件。
3. **漂移检测**：YAML 定义与数据库当前结构不一致时能被发现。
4. **修正闭环**：人工修正被记录下来，经审批后才合并进 MDL。

本方案的目标是补齐这四项，同时保持 YAML 为唯一的事实来源（方便 git 管理），不引入数据库或服务端依赖。

**不在本期范围内**：从数据库自动生成本体（需要 LLM，单独立项）、Web 界面、HTTP API。

## 2. 现状（已核对代码）

| 能力 | 现有实现 | 缺口 |
|---|---|---|
| 模型元数据 | `models/<name>/metadata.yml`，`properties` 为自由字典，会写入 `target/mdl.json` | 没有认证、负责人等约定字段 |
| 引擎对未知字段的处理 | `core/janus-core-base/manifest-macro` 中的 `Model` 结构没有 `properties` 字段，也没有 `deny_unknown_fields`，未知字段被静默忽略 | 引擎不会强制任何元数据 |
| 查询返回 | `run_sql` 返回 `columns`、`rows`、`row_count`、`truncated` | 没有来源信息 |
| 策略层 | `core/janus/src/janus/policy.py` 在执行前检查 SQL 是否只读（已验证会拦截 DROP、DELETE、INSERT、COPY、PRAGMA、ATTACH） | 没有元数据相关的规则 |
| 漂移检测 | `janus memory check` 检查知识文件与检索索引的差异 | 不检查 YAML 与数据库结构的差异 |
| 连接器 | `ConnectorABC` 只有 `query`、`dry_run`、`close` | 不能读取表结构、主键、外键 |
| 修正 | `store_query` 保存 NL→SQL 对；`memory` 召回 | 没有人工审批的修正流程 |

## 3. 设计

### 3.1 认证与负责人（P1）

在模型和列的 `properties` 中约定以下字段：

```yaml
name: orders
properties:
  certified: "true"        # 字符串，与现有 properties 保持一致
  owner: finance-team
  certified_by: alice
  certified_at: "2026-11-01"
```

- 引擎不读取这些字段，所以不需要改 Rust 代码。
- `policy.py` 增加一条规则：查询引用了未认证的模型时，在结果中附加 `warnings`。是否阻止由配置决定（`~/.janus/config.json` 增加 `require_certified: false` 默认值）。
- `janus context validate` 检查字段取值是否合法，例如 `certified` 只能是 `"true"` 或 `"false"`。
- `janus context show` 和 `describe_model` 输出中显示认证状态。

**关键约束**：这些字段只在 Python 层生效。直接使用引擎（比如 `janus-core-py` 的 SDK）时不会检查它们，文档需要说明。

### 3.2 溯源（P1）

`run_sql` 和 `query_cube` 的返回值增加 `provenance` 字段：

```json
{
  "columns": ["id", "amount"],
  "rows": [...],
  "row_count": 2,
  "truncated": false,
  "provenance": {
    "models": ["orders"],
    "cubes": [],
    "knowledge": ["knowledge/sql/total-revenue.md"],
    "certified": {"orders": true},
    "expanded_sql": "SELECT ... FROM ..."
  }
}
```

- `models` 和 `cubes`：从 `dry_plan` 的展开结果中收集。`dry_plan` 已经能给出展开后的 SQL，所以不需要额外解析。
- `knowledge`：由 `recall_queries` 命中的文件记录。
- `expanded_sql` 默认不返回，由参数 `include_sql: bool = False` 控制，避免结果过大。

### 3.3 漂移检测：`janus context diff`（P2）

比较 YAML 定义与数据库当前结构，报告：

- 数据库有、YAML 没有的表或列
- YAML 有、数据库没有的表或列
- 类型不一致的列（先经过 `janus utils parse-type` 统一类型再比较）
- 主键不一致

输出格式与 `janus memory check` 保持一致，支持 `--json`。退出码：无差异为 0，有差异为 1，便于 CI 使用。

依赖：需要连接器提供结构读取能力（见 3.4）。

### 3.4 连接器结构读取（P2，是 3.3 和 3.5 的前提）

在 `ConnectorABC` 增加可选方法，默认抛出 `NotImplementedError`：

```python
def list_tables(self, schema: str | None = None) -> list[TableInfo]: ...
def list_columns(self, table: TableInfo) -> list[ColumnInfo]: ...
def list_keys(self, table: TableInfo) -> KeyInfo: ...   # 主键和外键
```

实现策略：

- 大多数 SQL 连接器可以用 `information_schema`（或 ClickHouse、Snowflake 等的等价视图）实现，可以先做一个通用实现，再针对特殊连接器覆盖。
- 第一批支持：`postgres`、`mysql`、`duckdb`、`snowflake`、`bigquery`。其余连接器在文档中标注"暂不支持 diff 和 draft"。
- 对于 `local_file` 类的 DuckDB 数据源，用 DuckDB 的 `information_schema`。

### 3.5 草稿生成：`janus context draft --from-db`（P3）

从数据库生成候选的 MDL 草稿，**不直接修改项目**：

- 输出到 `draft/` 目录，结构与 `models/` 相同。
- 每个模型带 `properties.draft: "true"`，等待人工确认后去掉。
- 只做确定性的工作：表结构、类型、主键、外键。关联是否成立、字段含义等需要人工判断。
- 可选的 `--suggest-terms` 参数会调用智能体或模型推断字段描述，**这一步需要 LLM，默认关闭**。

确认方式：`janus context draft apply <模型名>` 把草稿移入 `models/`，并去掉 `draft` 标记。

### 3.6 修正队列（P4）

智能体不直接修改 MDL。流程如下：

1. 智能体或用户调用新的 MCP 工具 `propose_correction`，参数包括：涉及的模型、问题描述、建议的修改（YAML 片段）。
2. 修正写入 `knowledge/corrections/<时间戳>-<slug>.yml`，状态为 `pending`。
3. 人工运行 `janus context review` 列出待处理修正，逐条 `approve` 或 `reject`。
4. `approve` 时把修改应用到对应的 `metadata.yml`，并把状态改为 `applied`，保留文件作为审计记录。

`propose_correction` 属于写操作，需要 `--allow-write` 才启用，与 `store_query` 相同。

### 3.7 API（P5，暂缓）

如果需要 HTTP 访问，新增 `janus serve api`，复用 MCP 工具的实现。在前面几项稳定之前不做。

## 4. 变更清单

| 文件 | 变更 |
|---|---|
| `core/janus/src/janus/policy.py` | 认证相关的警告规则 |
| `core/janus/src/janus/mcp_server.py` | `provenance` 字段；`propose_correction` 工具（需 `--allow-write`） |
| `core/janus/src/janus/context_cli.py` | `diff`、`draft`、`review` 子命令；`validate` 检查认证字段 |
| `core/janus/src/janus/connector/base.py` | `list_tables`、`list_columns`、`list_keys` 可选方法 |
| `core/janus/src/janus/connector/{postgres,mysql,duckdb,snowflake,bigquery}.py` | 结构读取的实现 |
| `core/janus/src/janus/config.py`（或现有配置入口） | `require_certified` 配置项 |
| `docs/core/guides/` 和 `docs/core/reference/cli.md` | 新命令和字段说明（中英文） |

不需要修改 `core/janus-core*`（Rust）。

## 5. 测试计划

按照仓库的贡献规范，测试必须调用真实代码并能失败：

- **认证**：构造一个带 `certified: "false"` 模型的临时 DuckDB 项目，断言查询结果中出现对应警告；`require_certified: true` 时断言查询被拒绝。
- **溯源**：断言 `provenance.models` 与 `dry_plan` 展开结果中的表一致。
- **diff**：分别构造新增列、删除列、类型变化三种情况，断言退出码和输出条目。在 DuckDB 上做真实测试，不 mock 连接器。
- **draft**：对临时 DuckDB 数据库生成草稿，断言生成的 YAML 通过 `context validate`，且没有修改 `models/`。
- **修正队列**：断言 `propose_correction` 在没有 `--allow-write` 时被拒绝；`approve` 后 `metadata.yml` 的内容与建议一致。
- **CI**：新测试放在 `tests/unit/`，不放在需要额外依赖的目录里，否则默认作业不会执行。

## 6. 里程碑

| 阶段 | 内容 | 验收 |
|---|---|---|
| M1（P1） | 认证字段、策略警告、溯源 | 上述认证和溯源测试通过 |
| M2（P2） | 连接器结构读取（DuckDB、Postgres 先行）、`context diff` | diff 在两种数据库上通过测试 |
| M3（P3） | `context draft`，`--suggest-terms` 默认关闭 | 草稿通过 validate，不改动 `models/` |
| M4（P4） | 修正队列 | 审批前后文件内容符合预期 |
| M5（P5） | HTTP API | 暂缓，待决定 |

## 7. 风险与开放问题

- **元数据不被引擎强制**：认证字段只在 Python 层生效。需要决定是否接受这一限制，还是把字段加入 Rust 结构并做强制校验（改动更大，涉及 `janus-core-base` 和 `janus-mdl` 的 schema）。
- **连接器覆盖不全**：22 个连接器中，结构读取只实现 5 个，其余不能用 diff 和 draft。需要确认这一范围是否可以接受。
- **LLM 依赖**：`--suggest-terms` 需要模型。默认关闭，所以核心功能不依赖模型。
- **许可证**：auto-ontology 为 Apache-2.0，但 README 说明不接受外部贡献。本方案只借鉴思路，不复制代码。
- **大型 schema 的性能**：`diff` 和 `draft` 在表数量很多时可能较慢，需要分页或按 schema 过滤（`--schema`）。
- **仓库当前的分支状态**：本方案基于 `janus-rename` 分支。如果后续工作要在 `claude/bold-turing-ba0gxe` 上进行，需要先确认。

## 8. 验收标准

- 所有新增命令都有 `--help`，并在 `docs/core/reference/cli.md` 中有对应说明。
- 新增测试全部通过，且不依赖 `memory` 额外依赖或外部服务。
- 现有的 `janus context validate`、`janus --sql`、`janus memory check` 的行为不变。

## 9. 实现状态

| 阶段 | 状态 | 实现位置 | 与方案的差异 |
|---|---|---|---|
| P1 认证与 Rust 强制执行 | 完成 | `mdl/mod.rs`（`require_certified`）、`model/certification.py`、`context.py`（validate）、`mcp_server.py`、`engine.py` | `warnings` 由 MCP 层结果附加，而不是 `policy.py`，因为策略层拿不到查询结果 |
| P1 溯源 | 完成 | `engine.query_with_provenance`、`mcp_server._with_provenance` | `models` 取自展开后 SQL 中的 CTE 名称，只包含实际被读取的模型 |
| P2 连接器结构读取 | 完成（20 个 `DataSource`） | `connector/introspection.py`、`connector/factory.py` | 实际 `DataSource` 有 20 个（不是 22 个）。只有 DuckDB 做了真实数据库测试；其余方言的 SQL 未经过对应服务器验证。Trino、Athena、DataFusion、Spark 不能读取主键 |
| P2 `context diff` | 完成 | `context_diff.py`、`context_cli.py` | 退出码：0 无差异，1 有差异，2 无法读取数据库 |
| P3 `context draft --from-db` | 完成 | `context_draft.py` | 未实现 `--suggest-terms`（LLM 推断），按方案默认关闭 |
| P4 修正队列 | 完成 | `context_corrections.py`、`mcp_server.py`（`propose_correction`）、`context_cli.py`（`review`） | 受保护字段：`name`、`table_reference`、`ref_sql` |
| P5 HTTP API | 完成 | `api_server.py`、`serve_cli.py`（`serve api`） | 只提供查询和模型接口，不含写入。非回环地址必须提供 token |

### 已知限制

- 结构读取已在真实数据库上验证：DuckDB，以及 PostgreSQL 16（`ansi` flavor，见 `tests/connectors/test_postgres_introspection.py`，CI 中由 postgres 容器运行）。MySQL、Oracle、ClickHouse、BigQuery、Spark 等连接器的 SQL 仍未在对应服务器上验证。redshift、canner、snowflake、databricks 的 flavor 分类是依据经验判断，未经查证。
- `memory` 额外依赖缺失时，`tests/unit/test_memory.py` 中 6 个用例失败（`huggingface_hub` 未安装），与本次改动无关。

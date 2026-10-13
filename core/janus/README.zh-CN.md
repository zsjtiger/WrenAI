# janusai

🌐 [English](./README.md) · **简体中文**

[![PyPI version](https://img.shields.io/pypi/v/janusai.svg)](https://pypi.org/project/janusai/)
[![Python](https://img.shields.io/pypi/pyversions/janusai.svg)](https://pypi.org/project/janusai/)
[![License](https://img.shields.io/pypi/l/janusai.svg)](https://github.com/CrossNow/JanusAI/blob/main/LICENSE)

Janus AI 命令行工具与 Python SDK —— 面向 20+ 数据源的语义 SQL 层。

通过 [MDL（Modeling Definition Language，建模定义语言）](https://docs.crossnow.cn/) 语义层转换自然 SQL 查询，并在你的数据库上执行。基于 [Apache DataFusion](https://datafusion.apache.org/) 构建。

## 安装

```bash
pip install janusai                 # Core (DuckDB included)
pip install 'janusai[postgres]'     # PostgreSQL
pip install 'janusai[mysql]'        # MySQL
pip install 'janusai[bigquery]'     # BigQuery
pip install 'janusai[snowflake]'    # Snowflake
pip install 'janusai[clickhouse]'   # ClickHouse
pip install 'janusai[trino]'        # Trino
pip install 'janusai[mssql]'        # SQL Server
pip install 'janusai[databricks]'   # Databricks
pip install 'janusai[redshift]'     # Redshift
pip install 'janusai[spark]'        # Spark
pip install 'janusai[athena]'       # Athena
pip install 'janusai[oracle]'       # Oracle
pip install 'janusai[memory]'       # Schema & query memory (LanceDB)
pip install 'janusai[memory-onnx]'  # Same, torch-free (onnxruntime instead of PyTorch)
pip install 'janusai[ui]'           # Browser-based profile form (starlette + uvicorn)
pip install 'janusai[main]'         # memory + interactive prompts + ui
pip install 'janusai[all]'          # All connectors + main
```

需要 Python 3.11+。

## 快速开始

**1. 初始化项目** —— 生成基于 YAML 的 MDL 项目骨架：

```bash
mkdir my-project && cd my-project
janus context init
```

这会创建 `janus_project.yml`、`models/` 和 `views/`。编辑 `janus_project.yml` 设置 `data_source`，并在 `models/` 下添加模型：

```yaml
# janus_project.yml
schema_version: 2
name: my_project
catalog: janus
schema: public
data_source: postgres
```

```yaml
# models/orders/metadata.yml
name: orders
table_reference:
  schema: mydb
  table: orders
columns:
  - name: order_id
    type: integer
  - name: customer_id
    type: integer
  - name: total
    type: double
  - name: status
    type: varchar
primary_key: order_id
```

> **已经有 MDL JSON？** 可直接导入：
> `janus context init --from-mdl path/to/mdl.json`

**2. 配置连接配置档：**

```bash
# Browser form (recommended, requires janusai[ui])
janus profile add my-db --ui

# Interactive terminal prompts
janus profile add my-db --interactive

# Import from an existing connection file
janus profile add my-db --from-file connection_info.json
```

**3. 构建 manifest：**

```bash
janus context build
```

这会把 YAML 文件编译为 `target/mdl.json`。在项目目录内运行查询时，CLI 会自动发现该文件。

**4. 运行查询：**

```bash
janus --sql 'SELECT order_id FROM "orders" LIMIT 10'
```

`janus` 会从当前目录向上查找 `janus_project.yml`，并使用 `target/mdl.json`。你也可以通过 `--mdl path/to/mdl.json` 显式指定。

完整的 CLI 参考和各数据源连接字段参考，请见 [`docs/cli.md`](docs/cli.md) 和 [`docs/connections.md`](docs/connections.md)。

**4a.（可选）使用 cube 进行聚合查询** —— 在 `cubes/` 下定义 cube，然后使用结构化输入进行查询，而无需手写 `GROUP BY` SQL：

```bash
janus cube list
janus cube describe revenue
janus cube query --cube revenue --measures total --time-dimension "order_date:month"
```

转换器会为你生成 `DATE_TRUNC` / `GROUP BY` / `WHERE` 子句，并通过与 `janus --sql` 相同的引擎路径执行。完整的 YAML 结构请参阅 [Cube 指南](../../docs/core/guides/cubes.md)，所有参数请参阅 [CLI 参考](../../docs/core/reference/cli.md#janus-cube--pre-aggregation-queries)。

**5.（可选）配置安全策略** —— 创建 `~/.janus/config.json`：

```json
{
  "strict_mode": true,
  "denied_functions": ["pg_read_file", "dblink", "lo_import"]
}
```

| 键 | 默认值 | 说明 |
|-----|---------|-------------|
| `strict_mode` | `false` | 设为 `true` 时，查询中的每个表都必须在 MDL 中定义。引用未声明表的查询会在执行前被拒绝。 |
| `denied_functions` | `[]` | 查询中禁止使用的函数名列表（不区分大小写）。 |

**6.（可选）为语义搜索建立 schema 索引**（需要 `janusai[memory]`，或使用无需 torch 的安装方式 `janusai[memory-onnx]`）：

```bash
janus memory index                              # index MDL schema
janus memory fetch -q "customer order price"    # fetch relevant schema context
janus memory store --nl "top customers" --sql "SELECT ..."  # store NL→SQL pair
janus memory recall -q "best customers"         # retrieve similar past queries
janus memory watch                              # auto-reindex on schema/query changes
```

`memory-onnx` 通过 onnxruntime 而非 PyTorch 运行相同的权重，因此产生相同的向量，现有索引仍然有效 —— 它只是安装体积小得多，而不是另一种索引。当两个 extra 同时存在时，使用 onnx；设置 `JANUS_EMBEDDING_BACKEND=sentence-transformers` 可覆盖，`janus memory status` 会报告当前生效的是哪一个。

**7.（可选）构建可分享的 CReport 应用** —— 将上下文层转换为浏览器端仪表盘（由 `janus-core-wasm` 驱动），并部署到 Vercel 或 Cloudflare Pages。CLI 负责生成构建指令和确定性状态；由智能体根据该指令编写应用：

```bash
janus creport build sales --prompt "orders dashboard" --data-mode snapshot  # print build instruction
# agent authors apps/sales/ from the instruction (mdl.json + data/*.parquet)
janus creport register sales --data-mode snapshot   # record the app
janus creport verify sales                          # preflight (files, MDL, data, secret scan)
janus creport open sales                            # local preview
janus creport deploy sales --provider vercel        # ship a shareable URL (preview; --prod for production)
```

令牌从环境变量 / `.env` 中读取（`VERCEL_TOKEN` / `CLOUDFLARE_API_TOKEN`），而非 CLI 参数；Cloudflare 需要已安装 `wrangler`。请参阅 [CReport 指南](../../docs/core/guides/creport.md) 和 [CLI 参考](../../docs/core/reference/cli.md#janus-creport--build--deploy-creport-apps)。

**8.（可选）启动 MCP 服务器** —— 将项目的查询、schema 和知识工具暴露给 Claude Desktop/Code、Cursor 或任何 MCP 客户端。直接在进程内基于编译后的 MDL 运行 —— 无需单独的服务：

```bash
janus serve mcp                                # stdio (default) — client spawns this as a child process
janus serve mcp --transport http --port 8080   # local Streamable HTTP for other clients
```

需要先运行过 `janus context build`，并安装 `mcp` extra：`pip install 'janusai[mcp]'`。完整的工具/资源列表和客户端配置请参阅 [MCP 指南](../../docs/core/guides/mcp.md) 和 [CLI 参考](../../docs/core/reference/cli.md#janus-serve--mcp-server)。

---

## 连接配置档

配置档允许你在 `~/.janus/profiles.yml` 中存储命名的连接配置，并在它们之间轻松切换 —— 适用于在多个数据库或环境间工作的场景。

```bash
# Add a profile (browser form, interactive prompts, or file import)
janus profile add prod --ui                        # opens http://localhost:<port>
janus profile add staging --interactive            # terminal prompts
janus profile add local --from-file conn.json      # import existing file

# List and switch profiles
janus profile list                                 # * marks the active profile
janus profile switch prod

# Inspect a profile (sensitive fields masked)
janus profile debug prod

# Remove a profile
janus profile rm old-profile --force
```

`--ui` 参数会打开一个基于浏览器的表单，根据各数据源的 schema 自动推导字段 —— 包括 BigQuery 凭据的文件上传、Databricks/Redshift 的变体选择，以及全部 20+ 个受支持数据源的合理默认值。需要 `pip install 'janusai[ui]'`。

配置档激活后，`janus` 会自动使用它：

```bash
janus profile switch prod
janus --sql 'SELECT COUNT(*) FROM "orders"'        # connects using prod profile
```

---

## Python SDK

```python
import base64, orjson
from janus import JanusEngine, DataSource

manifest = { ... }  # your MDL dict
manifest_str = base64.b64encode(orjson.dumps(manifest)).decode()

with JanusEngine(manifest_str, DataSource.mysql, {"host": "...", ...}) as engine:
    result = engine.query('SELECT * FROM "orders" LIMIT 10')
    print(result.to_pandas())
```

---

## 开发

前提条件：`just` 和 `uv`。（仅下方的本地引擎命令需要 Rust + Cargo。）

### 标准安装（无需 Rust 工具链）

```bash
just install        # uv sync — pulls the prebuilt janus-core-py wheel from PyPI
just lint           # Ruff format check + lint
just format         # Auto-fix
```

`just install` 是普通的 `uv sync`：它会安装已锁定的预构建 `janus-core-py` 引擎绑定，以及 uv 默认 `dev` 依赖组中的开发工具。无需编译。这已足以完成所有 Python 侧的开发。如需数据源 extra，请使用 `just install-extra <extra>` 或 `just install-all`。

### 引擎开发（修改 Rust 核心）

仅当你修改了 `../janus-core-py`（或 `../janus-core`），并希望 `core/janus` 使用你的本地构建运行时才需要。需要 Rust + Cargo。

```bash
just install-local    # uv sync + build the local wheel + overlay it into .venv
just use-local-core   # rebuild + re-overlay after each subsequent Rust change
```

运行类 recipe（`just test*`、`just lint`、`just dev`）使用 `uv run --no-sync`，因此不会把本地覆盖的引擎回退为锁文件中的版本。如果依赖发生变化，请先重新运行安装 recipe。

| 命令 | 运行内容 | 需要 Docker |
|---------|-------------|---------------|
| `just test-unit` | 单元测试（引擎、CTE 重写器、字段注册表、配置档） | 否 |
| `just test-duckdb` | DuckDB 连接器测试 | 否 |
| `just test-postgres` | PostgreSQL 连接器测试 | 是 |
| `just test-mysql` | MySQL 连接器测试 | 是 |
| `just test` | 全部测试 | 是 |

Profile web 测试（`test_profile_web.py`）需要 `janusai[ui]`：

```bash
uv sync --extra ui
uv run --no-sync pytest tests/test_profile_web.py -v
```

## 发布

```bash
./scripts/publish.sh            # Build + publish to PyPI
./scripts/publish.sh --test     # Build + publish to TestPyPI
./scripts/publish.sh --build    # Build only
```

## 许可证

Apache-2.0

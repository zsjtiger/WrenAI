# CLI 参考

## 默认命令：query

运行 `janus --sql '...'` 会执行查询并打印结果，等同于 `janus query --sql '...'`。

```bash
janus --sql 'SELECT COUNT(*) FROM "orders"'
janus --sql 'SELECT * FROM "orders" LIMIT 5' --output csv
janus --sql 'SELECT * FROM "orders"' --limit 100 --output json
```

输出格式：`table`（默认）、`csv`、`json`。

## `janus query`

执行 SQL 并返回结果。

```bash
janus query --sql 'SELECT order_id, total FROM "orders" ORDER BY total DESC LIMIT 5'
```

## `janus dry-plan`

把 MDL SQL 转译为数据源对应方言的原生 SQL。不需要数据库连接。

```bash
janus dry-plan --sql 'SELECT order_id FROM "orders"'
janus dry-plan --sql 'SELECT order_id FROM "orders"' -d postgres  # 显式指定数据源，无需连接文件
```

## `janus dry-run`

在真实数据库上对 SQL 执行 dry-run，不返回任何行。成功时输出 `OK`，失败时输出 `Error: <reason>`。

```bash
janus dry-run --sql 'SELECT * FROM "orders" LIMIT 1'
# OK

janus dry-run --sql 'SELECT * FROM "NonExistent"'
# Error: table not found ...
```

## 覆盖默认设置

当 `~/.janus/mdl.json` 和 `~/.janus/connection_info.json` 存在时，所有参数都是可选的。

数据源始终从 `connection_info.json` 中的 `datasource` 字段读取（或从内联的 `--connection-info` 值中读取）。只有 `dry-plan` 接受 `--datasource` / `-d` 作为覆盖参数，用于在没有连接文件时仅做转译。

```bash
janus --sql '...' \
  --mdl /path/to/other-mdl.json \
  --connection-file /path/to/prod-connection_info.json
```

也可以直接内联传入连接信息：

```bash
janus --sql 'SELECT COUNT(*) FROM "orders"' \
  --connection-info '{"datasource":"mysql","host":"localhost","port":3306,"database":"mydb","user":"root","password":"secret"}'
```

扁平格式和封装（envelope）格式都可以接受：

```bash
# 扁平格式
{"datasource": "postgres", "host": "localhost", "port": 5432, ...}

# 封装格式（会自动解包）
{"datasource": "duckdb", "properties": {"url": "/data", "format": "duckdb"}}
```

---

## `janus profile import dbt`

把 dbt 的当前 target 从 `profiles.yml` 导入到 `~/.janus/profiles.yml`。

```bash
janus profile import dbt --project-dir ./jaffle_shop
janus profile import dbt --project-dir ./jaffle_shop --target prod --name jaffle-prod
```

常用参数：`--profiles-path`、`--profile`、`--target`、`--name`、`--no-activate`。

## `janus context import dbt`

从 dbt 产物生成一个 Janus 项目。

```bash
janus context import dbt --project-dir ./jaffle_shop --path ./janus-jaffle
janus context import dbt --project-dir ./jaffle_shop --path ./janus-jaffle --dry-run
```

需要 `target/manifest.json` 和 `target/catalog.json`，请先运行 `dbt build` 和 `dbt docs generate`。参见 [dbt 集成](/oss/guides/dbt-integration)（英文版）。

---

## `janus context upgrade`

把项目升级到最新布局（`schema_version` 5）。只向前升级，且幂等；v4 → v5 这一步会创建 `knowledge/` 骨架。

```bash
janus context upgrade --dry-run   # 预览将创建或修改的文件
janus context upgrade             # 执行升级
janus context upgrade --to 5      # 指定目标版本
```

要把 `instructions.md` 和 LanceDB 记忆迁移到 `knowledge/`，参见[迁移指南](/oss/reference/migration)（英文版）。

---

## `janus docs`：连接信息

### `janus docs connection-info <datasource>`

打印某个数据源所需的和可选的连接字段。

```bash
janus docs connection-info postgres
janus docs connection-info bigquery
janus docs connection-info snowflake
```

在创建配置文件之前，用它来确认需要哪些字段。

---

## `janus memory`：Schema 与查询记忆

Schema 和 NL-SQL 记忆。NL→SQL 对保存在 `knowledge/sql/*.md` 中（这是事实来源），LanceDB 索引是由它们重新构建的派生产物。

`store`、`index` 和 `recall` **不需要**任何额外依赖即可工作：问答对直接写入并搜索 `knowledge/sql/`（基于 token 或子串匹配）。只有需要**语义**（嵌入）召回和 Schema 搜索（`janus memory fetch`）时，才需要安装 `memory` 扩展：

```bash
pip install 'janusai[memory]'
# 或与 main 组合，以使用浏览器界面和交互式提示
pip install 'janusai[memory,main]'
```

后端会自动选择：安装了 `memory` 扩展时使用 LanceDB，否则使用无依赖的 grep 后端。可以通过 `JANUS_MEMORY_BACKEND=grep|lancedb` 强制指定。所有 `memory` 子命令都接受 `--path DIR`，用于覆盖 LanceDB 的存储位置（默认 `~/.janus/memory/`）。

> **注意：** `memory` 扩展包含约 800MB 的大型未签名原生库（lancedb 以及 sentence-transformers/torch）。在 macOS 上，第一次加载 memory 相关功能的命令可能会触发一次性的 XProtect/Gatekeeper 扫描，并暂停最多约一分钟，之后才会完成。这是 macOS 的正常行为，不是 Janus 的错误，并且每次安装或新建虚拟环境时只发生一次。由于 memory 采用惰性加载，轻量的非 `memory` 命令不受影响，扫描只会推迟到你第一次真正使用 memory 时，而不是被消除。

### 混合策略：全文与嵌入搜索

向 LLM 提供 Schema 上下文时需要权衡：

- **小型 Schema**：完整的纯文本描述可以轻松放进 LLM 的上下文窗口，效果更好，因为 LLM 能看到完整的结构（模型与列的关系、join 路径、主键），而不是向量搜索返回的零散片段。
- **大型 Schema**：完整文本超出了单次提示的实际可承受范围，因此需要嵌入搜索，只检索相关片段。

`janus memory fetch` 会根据生成的纯文本描述的**字符数**自动选择策略：

| Schema 大小 | 阈值 | 策略 |
|---|---|---|
| 低于 30,000 字符（约 8K token） | 默认 | 返回完整纯文本 |
| 高于 30,000 字符 | 默认 | 返回嵌入搜索结果 |

阈值以字符数（而非 token 数）衡量，因为字符数计算是免费的，而精确的 token 计数需要分词器。英文的字符与 token 比例约为 4:1；中文压缩率较低（约 1.5:1），因此以中文为主的 Schema 会更早切换到嵌入搜索，这是更保守的方向。

默认阈值（30,000 字符）可以通过 `--threshold` 覆盖。

### `janus memory index`

构建语义索引：包括 Schema 条目（模型、列、关联关系、视图），以及来自 `knowledge/sql/*.md` 的 NL→SQL 对（重复运行会与 markdown 保持一致）。需要 `memory` 扩展。没有它时，grep 后端直接读取 `knowledge/sql/`，因此没有需要构建的内容，该命令是空操作。

```bash
janus memory index                          # 使用 ~/.janus/mdl.json
janus memory index --mdl /path/to/mdl.json  # 显式指定 MDL 文件
```

### `janus memory watch`

监视项目源文件，并在变化时自动重新建立索引，使你在积极建模时语义召回不会返回过期的 Schema。它会按固定间隔轮询 `target/mdl.json` 和 `knowledge/sql/*.md`；当内容指纹发生变化时，执行等同于 `janus memory index` 的操作。如果一次重建索引失败，变化会保持待处理状态，并在下一次轮询时重试，更新不会被静默丢弃。运行直到按下 `Ctrl+C`。

需要 `memory` 扩展（它维护的索引由 LanceDB 支持）。使用 grep 后端时没有需要保持新鲜的派生索引，该命令会直接退出并给出提示。

| 参数 | 说明 |
|------|-------------|
| `--interval`, `-i` | 轮询间隔（秒，最小 1）。默认：`5`。 |
| `--reindex-on-start` / `--no-reindex-on-start` | 启动时先重建一次索引，再开始监视。默认：关闭。 |
| `--max-polls` | 轮询 N 次后停止（主要用于脚本和测试）。默认：运行直到 Ctrl+C。 |
| `--mdl` | 显式指定 MDL 文件（必须位于被监视的项目根目录下）。 |
| `--path` | 要监视的项目根目录。默认为发现的项目。 |

```bash
janus memory watch                       # 每 5 秒轮询，变化时重建索引
janus memory watch -i 2                   # 每 2 秒轮询
janus memory watch --reindex-on-start     # 在第一个间隔之前确保索引是最新的
```

### `janus memory describe`

把完整 Schema 以结构化纯文本打印出来。不需要嵌入或 LanceDB，这只是把 MDL manifest 纯粹地转换为人类与 LLM 都可读的格式。

```bash
janus memory describe                          # 使用 ~/.janus/mdl.json
janus memory describe --mdl /path/to/mdl.json
```

### `janus memory fetch`

为 LLM 获取 Schema 上下文。根据 Schema 大小自动选择最佳策略：小型 Schema 返回完整纯文本，大型 Schema 使用嵌入搜索。

使用搜索策略时，可选的 `--type` 和 `--model` 过滤器可以缩小结果范围。

```bash
janus memory fetch -q "customer order price"
janus memory fetch -q "revenue" --type column --model orders
janus memory fetch -q "order date" --threshold 50000 --output json
```

| 参数 | 说明 |
|------|-------------|
| `-q, --query` | 搜索查询（必填） |
| `--mdl` | MDL JSON 文件路径 |
| `-l, --limit` | 搜索策略的最大结果数（默认：5） |
| `-t, --type` | 过滤：`model`、`column`、`relationship`、`view`（仅搜索策略） |
| `--model` | 按模型名称过滤（仅搜索策略） |
| `--threshold` | 完整文本与搜索之间的字符阈值（默认：30,000） |
| `-o, --output` | 输出格式：`table`（默认）、`json` |

### `janus memory store`

保存一对自然语言到 SQL 的问答。它会写入 `knowledge/sql/<slug>.md`（事实来源，不需要任何额外依赖），并在安装了 `memory` 扩展时将其索引到 LanceDB 中。

```bash
janus memory store \
  --nl "show top customers by revenue" \
  --sql "SELECT c_name, sum(o_totalprice) FROM orders JOIN customer GROUP BY 1 ORDER BY 2 DESC" \
  --datasource postgres
```

### `janus memory recall`

搜索已保存的 NL-SQL 问答对：安装了 `memory` 扩展时进行语义相似度匹配，否则进行 token 或子串匹配（grep）。每条结果都会标注其对应的 `knowledge/sql/*.md` 路径。

```bash
janus memory recall -q "best customers"
janus memory recall -q "monthly revenue" --datasource mysql --limit 5 --output json
```

| 参数 | 说明 |
|------|-------------|
| `-q, --query` | 搜索查询（必填） |
| `-l, --limit` | 最大结果数（默认：3） |
| `-d, --datasource` | 按数据源过滤 |
| `-o, --output` | 输出格式：`table`（默认）、`json` |

### `janus memory export`

一次性迁移：把现有的 LanceDB `query_history` 导出到 `knowledge/sql/*.md`（保留来源、时间戳和去重信息）。读取 LanceDB 需要 `memory` 扩展；LanceDB 数据保持不变。参见[迁移指南](/oss/reference/migration)（英文版）。

```bash
janus memory export                 # query_history → knowledge/sql/*.md
janus memory export --include-seed   # 同时导出自动生成的种子问答对
```

### `janus memory check`

报告 `knowledge/sql/*.md` 与派生索引之间的不一致（哪些用户问答对未被索引，或被索引但缺少 markdown 源文件）。

```bash
janus memory check
```

### `janus memory status`

显示索引统计信息：存储路径、表名和行数。

```bash
janus memory status
# Path: /Users/you/.janus/memory
#   schema_items: 47 rows
#   query_history: 12 rows
```

### `janus memory reset`

删除派生的 LanceDB 索引。你的 `knowledge/sql/*.md` 源文件会被**保留**，随时可以通过 `janus memory index` 重新构建索引。

```bash
janus memory reset          # 会要求确认
janus memory reset --force  # 跳过确认
```

---

## `janus cube`：预聚合查询

当 MDL 中定义了 Cube 时，对于聚合查询请使用 `janus cube`，而不是手写原始 SQL。转译器会根据结构化输入生成正确的 `GROUP BY`、`DATE_TRUNC` 和 `WHERE` 子句。

### `janus cube list`

列出已加载 MDL 中的所有 Cube，以及它们的度量和维度。

```bash
janus cube list
```

### `janus cube describe <name>`

以 JSON 格式美化打印完整的 Cube Schema：`baseObject`、度量（包括表达式）、维度、时间维度和层级。

```bash
janus cube describe revenue
```

### `janus cube query`

构建一个 CubeQuery，通过 janus-core 把它转译为 SQL，然后经由与 `janus --sql` 相同的路径执行。有两种输入模式：

**CLI 参数：**

```bash
janus cube query \
  --cube revenue \
  --measures total,order_count \
  --dimensions status \
  --time-dimension "order_date:month:2024-01-01,2025-01-01" \
  --filter "status:eq:completed" \
  --order-by "total:desc" \
  --limit 100
```

**JSON 输入**（`--from <file|->`）：

```bash
cat query.json | janus cube query --from -
```

| 参数 | 说明 |
|------|-------------|
| `--cube` | Cube 名称（使用 `--from` 时可省略） |
| `--measures` | 逗号分隔的度量名称（使用 `--from` 时可省略） |
| `--dimensions` | 逗号分隔的维度名称 |
| `--time-dimension` | `<name>:<granularity>[:start,end]`，一个时间维度，可带可选的日期范围 |
| `--filter` | 可重复。`<dimension>:<operator>[:value]`。对于 `in` / `not_in`，value 为逗号分隔的列表。 |
| `--order-by` | 可重复。`<member>:<direction>`，其中 direction 为 `asc` 或 `desc`；多个排序项用逗号分隔。该 member 必须被查询选中。 |
| `--limit` / `--offset` | 分页 |
| `--from <file\|->` | 从文件或标准输入加载 CubeQuery JSON。它提供完整的查询，因此上面的查询构建参数（包括 `--order-by`）都会被忽略。 |
| `--sql-only` | 打印生成的 SQL 并退出，不执行 |
| `--mdl` | MDL JSON 路径（默认为 `<project>/target/mdl.json`） |
| `--output` | `table`（默认）、`json`、`csv` |

**支持的粒度：** `year`、`quarter`、`month`、`week`、`day`、`hour`、`minute`。

**支持的过滤运算符：** `eq`、`neq`、`in`、`not_in`、`gt`、`gte`、`lt`、`lte`、`contains`、`starts_with`、`is_null`、`is_not_null`。

**排序：** `--order-by` 会按查询中选中的 member 排序，因此应与 `--limit` 配合使用，才能得到真正的 Top-N。省略它时保持默认排序（如果存在时间维度，则按时间维度排序）。排序方向只能是小写，同一个 member 重复出现，或出现了查询未选中的 member，都会被 janus-core 拒绝。

YAML 结构和校验规则，参见 [Cube 指南](../guides/cubes.md)。

---

## `janus serve`：MCP 服务器

把项目的查询、Schema 和知识工具作为本地 MCP 服务器提供给 MCP 客户端（Claude Desktop/Code、Cursor 或任何支持 MCP 的 IDE）。服务器在进程内嵌入引擎，没有独立后端，因此只要运行过 `janus context build`，就可以直接从项目目录启动。

### `janus serve mcp`

```bash
janus serve mcp                                  # stdio（默认）：由客户端作为子进程启动
janus serve mcp --transport http --port 8080     # 本地 Streamable HTTP，供多个或远程客户端使用
```

需要 `mcp` 扩展：`pip install 'janusai[mcp]'`。

| 参数 | 默认值 | 说明 |
|------|---------|-------------|
| `--transport` | `stdio` | `stdio` 或 `http` |
| `--host` | `127.0.0.1` | 绑定地址，仅用于 `--transport http` |
| `--port` | `8080` | 绑定端口，仅用于 `--transport http` |
| `--project` | 自动发现 | 覆盖项目根目录 |
| `--profile` | 当前激活的配置文件 | 连接配置文件名称 |
| `--allow-write` | 关闭 | 启用 `store_query` 写入工具 |
| `--no-connect` | 关闭 | 仅转译模式：禁用 `run_sql`、`dry_run`、`query_cube` |
| `--quiet` / `-q` | 关闭 | 不显示客户端注册帮助横幅 |

启动时，服务器会向 stderr 输出可直接复制的注册命令，对应你当前的调用方式：`--transport http` 时为 `claude mcp add` / `codex mcp add` 命令；stdio 模式则会额外给出 JSON 格式的 `mcpServers` 配置块（反映 `--project`、`--profile`、`--allow-write` 以及 `JANUS_HOME`）。传入 `--quiet` 可以关闭这些输出。

需要存在 `target/mdl.json`（先运行 `janus context build`），否则会报错并给出提示。如果项目源文件（`models/`、`views/`、`cubes/`、`relationships.yml`、`janus_project.yml`）比 `target/mdl.json` 更新，它会警告 MDL 可能已过期，但仍会继续提供服务。它从不自动构建。

### 客户端配置（stdio）

```json
{
  "command": "janus",
  "args": ["serve", "mcp"],
  "cwd": "/path/to/project"
}
```

使用 `--transport http` 时，让客户端连接 Streamable HTTP 端点 `http://<host>:<port>`，而不是启动子进程。默认绑定到 `127.0.0.1`；当前版本没有 Bearer Token 认证，请仅在本地使用。

### 工具

| 分组 | 工具 |
|---|---|
| 查询 | `run_sql`、`dry_run`、`dry_plan`、`query_cube` |
| Schema | `get_mdl`、`list_models`、`describe_model`、`get_data_source`、`list_cubes`、`describe_cube`、`list_functions` |
| 知识 | `get_instructions`、`recall_queries`、`get_context`、`describe_schema`、`list_stored_queries`、`list_knowledge` |
| 写入（`--allow-write`） | `store_query` |

`--no-connect` 模式下，`run_sql`、`dry_run` 和 `query_cube` 会被禁用。只有传入 `--allow-write` 时才会注册 `store_query`。

没有 `memory` 扩展时，知识工具会优雅降级：`get_context`（语义 Schema 检索，是 `recall_queries` 在 Schema 维度上的对应工具）会回退到完整的纯文本 Schema 描述；`describe_schema`（`get_mdl` 的人类可读版本）完全不需要可选依赖；`list_stored_queries` 会从 `knowledge/sql/*.md` 列出每一对 NL→SQL（而不仅是语义 top-k）；`list_knowledge` 会列出可通过下方 `janus://knowledge/{path}` 资源读取的所有文件。

### 资源与提示词

- `janus://mdl`：编译后的 MDL JSON
- `janus://instructions`：来自 `knowledge/rules/*.md` 的业务规则
- `janus://project`：项目名称、catalog、schema、数据源、schema_version 和 knowledge_schema_version
- `janus://agents`：项目的 `AGENTS.md`（如果存在）
- `janus://knowledge/{path}`：读取 `knowledge/` 下的任意文件（例如 `janus://knowledge/knowledge.yml`、`janus://knowledge/rules/general.md`）；拒绝任何会逃逸出项目 `knowledge/` 目录的路径
- `janus_workflow` 提示词：为连接的智能体打包了一套标准操作流程：schema → 指令 → 检索 → dry-run → run_sql → query_cube → 存储

### 安全

连接密钥只在服务器启动时从配置文件中解析一次，从不跨越 MCP 边界。客户端只能看到 SQL 文本、查询结果和元数据。

完整的客户端接入演示，参见 [MCP 指南](../guides/mcp.md)。

---

## `janus skills`：智能体工作流指南

CLI 内置了自己的智能体 Skill 内容。任何 AI 客户端都可以使用（内容相同，内容随 wheel 包一起分发，而不是存放在智能体缓存中）。

### `janus skills list`

列出可用的工作流指南。

```bash
janus skills list
```

### `janus skills get <name>`

把某个 Skill 的主指南打印到标准输出。目前提供五个名称：
`onboarding`、`usage`、`generate-mdl`、`dlt-connector`、`enrich-context`。

```bash
janus skills get onboarding              # 端到端地设置 Janus
janus skills get usage                   # 日常查询
janus skills get generate-mdl            # 从数据库 Schema 生成 MDL
janus skills get dlt-connector           # 通过 dlt 连接 SaaS 数据源
janus skills get enrich-context          # 补充业务上下文（单位、枚举、Cube）
```

### `janus skills get <name> --full`

把 Skill 的参考文档一并内联输出（有序排列，并用分隔符隔开）。对于没有 `references/` 的 Skill，输出与不带 `--full` 的形式完全相同。

### `janus skills get <name> --script <s>`

打印内置脚本的源代码到标准输出。目前提供：

```bash
janus skills get dlt-connector --script introspect_dlt > introspect_dlt.py
python introspect_dlt.py --duckdb-path ./pipeline.duckdb --output-dir ./project
```

---

## `janus ask`：提示词整形

把自然语言问题包装进两个内置模板之一，并把渲染后的提示词打印到标准输出。**它不会执行任何查询**，只是生成一段供智能体使用的提示词。

你必须明确选择一种模式（没有默认值，因为悄悄更改默认值会在升级后改变智能体的行为）。

### `janus ask "<question>" --guided`

面向能力较弱的 LLM。会在前面加上一个严格的任务流程（`janus context show` → `janus memory recall` → 编写 SQL → `janus dry-plan` → `janus query`）。

```bash
janus ask "top 5 customers by revenue" --guided
```

### `janus ask "<question>" --direct`

面向能力较强的 LLM。包装最少，由智能体自行决定运行哪些 janus 命令。

```bash
janus ask "monthly orders trend" --direct
```

## `janus creport`：构建与部署 CReport 应用

把项目的上下文层转换为可分享的浏览器端 CReport Web 应用（由 `janus-core-wasm` 驱动），并部署到 Vercel 或 Cloudflare Pages。

**CLI 与智能体的分工：** CLI 负责权威的构建说明和所有确定性状态（应用索引、verify、deploy）。智能体按照说明编写应用代码。`.janus/apps.yml` 只由 CLI 写入，绝不手动编辑。对应的智能体工作流指南是 `janus skills get creport`。

### `janus creport build <name>`

打印一份由项目数据补全的构建说明（包括使用固定版本 `janus-core-wasm` 的 wasm 接入方式、项目的模型和列清单、数据模式指导、验收标准以及目标目录）。它不会写入任何应用文件，只会在 `target/mdl.json` 缺失时先编译它。

```bash
janus creport build sales-overview --prompt "orders dashboard" --data-mode snapshot
# --prompt-file <file> / --prompt -    从文件或标准输入读取较长的提示词
# --data-mode snapshot|live            snapshot（默认）：把数据打包进应用
#                                      live：应用在查看时调用支持 CORS 的端点
```

### `janus creport register <name>` / `list` / `remove <name>`

由机器写入的应用索引（`<project>/.janus/apps.yml`）。

```bash
janus creport register sales-overview --data-mode snapshot   # 记录一个已编写的应用
janus creport list                                           # 应用、状态和部署状态
janus creport remove sales-overview                          # 删除索引条目（保留文件）
```

应用名称必须是简单的 slug（字母、数字、`_`、`-`）；包含路径分隔符的名称会被拒绝，以免逃逸出 `<project>/apps/`。

### `janus creport verify <name>`

确定性的部署预检（不需要浏览器）：检查必需文件是否存在、`mdl.json` 能否正常解析、snapshot 应用是否包含 `.parquet`/`.duckdb` 资产，并通过默认拒绝的密钥扫描检查是否存在内嵌凭据。`deploy` 会以此为前置条件。密钥扫描是尽力而为的纵深防御，不是绝对保证，永远不要内嵌密钥。

### `janus creport open <name>`

在本地提供已构建应用的预览服务（阻塞运行；Ctrl-C 停止）。

```bash
janus creport open sales-overview --port 8848   # 0 = 自动选择端口
```

### `janus creport deploy <name>`

先执行 verify，然后部署到用户的服务商账号，并返回可分享的 URL。默认部署为预览；`--prod` 会部署到生产环境（请先与用户确认）。

```bash
janus creport deploy sales-overview --provider vercel        # 或 cloudflare
janus creport deploy sales-overview --provider vercel --prod
```

- **令牌**从环境变量或 `.env` 文件中发现（`VERCEL_TOKEN` / `CLOUDFLARE_API_TOKEN`），绝不作为 CLI 参数传递。Cloudflare 还需要 `CLOUDFLARE_ACCOUNT_ID`。
- **Cloudflare** 会调用 `wrangler` CLI（`npm install -g wrangler`，或确保 `npx` 可用），因为 Pages 没有单一的内联上传 REST 端点。
- **Vercel Deployment Protection：** 新建的 Vercel 项目默认会对未登录的访问者返回 HTTP 401。要让 URL 公开，请在 Project → Settings → Deployment Protection 中关闭它。部署本身已经成功，只是 URL 被拦截了。

---

## `janus cloud`：将项目连接到 Janus Cloud

把本地 Janus 项目绑定到 Janus Cloud 项目的 git 仓库。**绑定关系就是 git remote**：你的机器上不会记录某个目录属于哪个项目。绑定之后，直接使用普通的 `git push` / `git pull` / `git diff` 即可；安全性也不依赖于再次通过这个 CLI。

有两种凭据，它们的有效期不同：

- **项目 API 密钥**是长期有效的。首次使用时会提示输入，保存在 `~/.janus/cloud.yml` 中（权限 `0600`，按 git 主机和项目 ID 索引），除了以 `Authorization` 请求头的形式发送之外，永远不会离开本机。
- **git 令牌**是一个短期有效的 JWT，每次 git 操作时都会由 git 自己调用的凭据辅助程序从该密钥铸造。它从不写入磁盘，因此令牌过期并不是问题：没有任何东西会长时间持有它，以至于延迟提交。

`--host` 在不同命令中含义不同，并且只在指向某个目标时才有默认值。在 `auth add` 和 `create` 中，它默认为 `https://cloud.crossnow.cn`；如果是自托管部署，请传入 URL。在 `link` 和 `auth remove` 中，它用于从已保存的凭据中*选择*，并且**没有**默认值，这是有意为之：为过滤条件设置默认值会隐藏你确实拥有的凭据。无论如何，没有提供协议时都默认使用 `https`。

`--git-host` 仅适用于 API 与 git 服务器位于不同主机的部署，例如自托管且没有统一入口的情况。在托管服务上，不需要传入它。

### `janus cloud auth add`

保存 git 用于认证的凭据，并配置 git 使用它。它不会操作任何目录，因此在克隆之前就可以使用。

```bash
janus cloud auth add --project 1234
janus cloud auth add --project 1234 --host https://janus.internal.example.com
```

它会把一个限定于 URL 的凭据辅助程序条目写入你的**全局** git 配置（此时还没有可以写入本地配置的克隆）。由于辅助程序会根据 git 传给它的路径判断应该为哪个项目铸造令牌，因此每个主机只需一个条目，就可以服务该主机上的所有项目。

如果 `PATH` 上的 `janus` 无法提供该辅助程序，它会在最开始就拒绝执行。一个 git 无法使用的已保存凭据，比没有凭据更糟。

### `janus cloud create`

把你已有的 Janus 项目转换为 Janus Cloud 项目：创建项目、连接其数据源、绑定当前目录并推送。推送本身就会部署模型。

```bash
janus cloud create --org 42 --type BIG_QUERY --connection-info-file ./conn.json
janus cloud create --org 42 --type POSTGRES --connection-info '{"host":"db","port":"5432","user":"u","password":"p","database":"d"}' --test-connection
```

组织密钥可以来自 `--org-key`、`JANUS_CLOUD_ORG_KEY` 环境变量，或交互式提示。它只用于创建项目并为该项目铸造它自己的密钥，并且**绝不**写入磁盘。

`--type` 不区分大小写，名称与 API 本身的命名一致，注意 `BIG_QUERY` 中的下划线。`--connection-info` 会被原样传递，因此其中的字段也遵循 API 的定义，并且不同数据源之间的字段不同。

**它的格式与 `janus profile` 不同，两者之间没有任何转换。** API 需要 camelCase 键，并且 BigQuery 的 `credentials` 是服务账号对象；而配置文件使用 snake_case 键，并且 `credentials` 是 base64 字符串。传入配置文件导出的内容会被拒绝。

**支持的类型以及每种类型的 `connectionInfo` 示例，参见 [Create a project → Database connectionInfo examples](https://janusai.readme.io/reference/post_projects#database-connectioninfo-examples)（英文）。** 该页面是权威来源；本 CLI 不维护自己的列表副本，因此在那里新增的数据源无需发布新的 CLI 版本即可在这里使用。

以下要求都会在**创建任何内容之前**检查，因此被拒绝时不会留下半成品项目：

- 该目录是一个 Janus 项目（有 `janus_project.yml`），且 YAML 能够正常编译。如果要从零开始创建新项目，请在 Janus Cloud 网页界面中创建。
- 同时提供了 `--type` 和连接信息。没有数据源的项目会被报告为仍需设置，并且本 CLI 之后无法再附加数据源。
- 该目录尚未绑定，不位于另一个 git 仓库内，并且 git 已配置身份信息。

模型通过 git 传输，而不是通过 API：manifest 只是为了校验项目而构建，随后就会被丢弃，推送会触发仓库的部署钩子。

### `janus cloud link`

把一个目录绑定到你已经执行过 `auth add` 的项目。可用于在第二台机器上克隆项目，或在 `unlink` 之后重新绑定。

```bash
janus cloud link                       # 当前目录
janus cloud link ./my-project --project 1234
```

如果上一次尝试中途失败，可以安全地重新运行。如果目录已经完全绑定，它会提示并且不会再次合并，获取更新请使用 `git pull`。

会以远程默认分支的名称命名本地分支，因此之后直接使用普通的 `git push` 即可。它会拒绝把一个项目的历史合并进另一个项目。

### `janus cloud unlink`

移除 `origin` remote。这就是完整的解绑操作：不调用服务器，项目本身不受影响。

```bash
janus cloud unlink
janus cloud unlink ./my-project --forget-key --yes
```

默认会保留你已保存的密钥，因为可能还有其他目录绑定着同一个项目。`--forget-key` 会同时删除该密钥，并移除该主机的凭据辅助程序条目；但只有在没有已保存的登录信息使用该主机时才会删除，因为该条目是该主机上所有项目共享的。

### `janus cloud auth list`

显示已保存的内容，但不显示密钥。

```bash
janus cloud auth list
```

```text
PROJECT  API HOST (--host)          GIT HOST (git talks to)   REPO
1234     https://cloud.crossnow.cn   https://cloud.crossnow.cn  org/42/1234/shared-data.git
```

两个主机列都会打印出来，因为它们的含义不同，并且可能不一样。**其他命令中的 `--host` 指的是 API 主机**，也就是你在 `auth add` 时提供的值。凭据文件是以 *git* 主机为索引的，因为这是 git 传给凭据辅助程序的全部信息。因此，如果你通过读取文件来查找 `--host` 的值，得到的会是错误的结果。这个命令就是为解决这个问题而存在的。

不带任何参数时不会显示密钥。

### `janus cloud auth remove`

删除已保存的凭据。不操作任何目录。

```bash
janus cloud auth remove --project 1234 --yes
```

### `janus cloud git-credential`

`auth add` 接入 git 的凭据辅助程序。由 git 调用，你不需要手动调用它。

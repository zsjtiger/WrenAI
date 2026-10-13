# CLI 参考

🌐 [English](./cli.md) · **简体中文**

## 默认命令 — query

直接运行 `janus --sql '...'` 会执行查询并打印结果。这与 `janus query --sql '...'` 相同。

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

将 MDL SQL 转换为数据源对应的原生方言 SQL。无需数据库连接。

```bash
janus dry-plan --sql 'SELECT order_id FROM "orders"'
janus dry-plan --sql 'SELECT order_id FROM "orders"' -d postgres  # explicit datasource, no connection file needed
```

## `janus dry-run`

在实际数据库上对 SQL 进行试运行，但不返回数据行。成功时输出 `OK`，失败时输出 `Error: <reason>`。

```bash
janus dry-run --sql 'SELECT * FROM "orders" LIMIT 1'
# OK

janus dry-run --sql 'SELECT * FROM "NonExistent"'
# Error: table not found ...
```

## 覆盖默认值

当 `~/.janus/mdl.json` 和 `~/.janus/connection_info.json` 都存在时，所有参数均为可选。

数据源始终从 `connection_info.json` 中的 `datasource` 字段读取（或从内联的 `--connection-info` 值中读取）。只有 `dry-plan` 接受 `--datasource` / `-d` 作为覆盖选项，用于在没有连接文件的情况下仅做转换。

```bash
janus --sql '...' \
  --mdl /path/to/other-mdl.json \
  --connection-file /path/to/prod-connection_info.json
```

或者以内联方式传入连接信息：

```bash
janus --sql 'SELECT COUNT(*) FROM "orders"' \
  --connection-info '{"datasource":"mysql","host":"localhost","port":3306,"database":"mydb","user":"root","password":"secret"}'
```

扁平格式和 MCP/web 包装格式均可接受：

```bash
# Flat format
{"datasource": "postgres", "host": "localhost", "port": 5432, ...}

# Envelope format (auto-unwrapped)
{"datasource": "duckdb", "properties": {"url": "/data", "format": "duckdb"}}
```

---

## `janus memory` — Schema 与查询记忆

基于 LanceDB 的语义记忆，用于 MDL schema 搜索和 NL→SQL 检索。使用 `main` 扩展包安装（包含 `memory`、`interactive`、`ui`）：

```bash
pip install 'janusai[main]'   # includes memory, interactive, ui
```

所有 `memory` 子命令都接受 `--path DIR` 参数，用于覆盖默认存储位置（`~/.janus/memory/`）。

> **注意：** `memory` 扩展包捆绑了约 800MB 的大型未签名原生库（lancedb 以及 sentence-transformers/torch）。在 macOS 上，首次加载 memory 组件的命令可能会触发一次性的 XProtect/Gatekeeper 扫描，并暂停最长约一分钟后才完成。这是 macOS 的正常行为，而非 Janus 错误，每次安装或新建虚拟环境时只发生一次。由于 memory 采用延迟加载，轻量的非 `memory` 命令不受影响；扫描只是被推迟到你第一次真正使用 memory 时，并未被消除。

### 混合策略：全文搜索与嵌入搜索

为 LLM 提供 schema 上下文时，需要权衡以下两点：

- **小型 schema** — 完整的纯文本描述可以轻松放入 LLM 的上下文窗口，效果更好，因为 LLM 能看到完整结构（model→column 关系、连接路径、主键），而不是向量搜索返回的零散片段。
- **大型 schema** — 完整文本超出了单次 prompt 的实际发送范围，因此需要嵌入搜索，只检索相关片段。

`janus memory fetch` 会根据生成的纯文本描述的**字符长度**自动选择策略：

| Schema 大小 | 阈值 | 策略 |
|---|---|---|
| 低于 30,000 字符（约 8K tokens） | 默认 | 返回完整纯文本 |
| 高于 30,000 字符 | 默认 | 返回嵌入搜索结果 |

阈值以字符（而非 token）计量，因为字符长度计算成本很低，而精确的 token 计数需要分词器。4:1 的字符与 token 比例适用于英文；CJK 文本的压缩率较低（约 1.5:1），因此以 CJK 为主的 schema 会更早切换到嵌入搜索，这是更保守的方向。

默认阈值（30,000 字符）可以通过 `--threshold` 覆盖。

### `janus memory index`

解析 MDL manifest，并使用本地嵌入将所有 schema 项（models、columns、relationships、views）索引到 LanceDB 中。

```bash
janus memory index                          # uses ~/.janus/mdl.json
janus memory index --mdl /path/to/mdl.json  # explicit MDL file
```

### `janus memory watch`

监视项目源文件，并在内容变化时自动重新索引，确保在你积极建模时，语义召回不会返回过时的 schema。它以固定间隔轮询 `target/mdl.json` 和 `knowledge/sql/*.md`；当其内容指纹发生变化时，运行等同于 `janus memory index` 的操作。失败的重新索引会保留待处理的变更，并在下一次轮询时重试，更新永远不会被静默丢弃。命令会一直运行，直到按下 `Ctrl+C`。

需要 `memory` 扩展包。使用 grep 后端时没有需要保持新鲜的派生索引，因此此命令会退出并给出提示信息。

| 标志 | 说明 |
|------|------|
| `--interval`, `-i` | 轮询之间的秒数（最小 1）。默认：`5`。 |
| `--reindex-on-start` / `--no-reindex-on-start` | 开始监视前，启动时重新索引一次。默认：关闭。 |
| `--max-polls` | 轮询 N 次后停止（主要用于脚本编写/测试）。默认：运行直到按下 Ctrl+C。 |
| `--mdl` | 显式指定 MDL 文件（必须位于被监视的项目根目录下）。 |
| `--path` | 要监视的项目根目录。默认为已发现的项目。 |

```bash
janus memory watch                    # poll every 5s, reindex on change
janus memory watch -i 2                # poll every 2s
janus memory watch --reindex-on-start  # ensure the index is fresh before the first interval
```

### `janus memory describe`

以结构化纯文本形式输出完整 schema。无需嵌入或 LanceDB，这只是把 MDL manifest 纯粹地转换为人类/LLM 可读的格式。

```bash
janus memory describe                          # uses ~/.janus/mdl.json
janus memory describe --mdl /path/to/mdl.json
```

### `janus memory fetch`

为 LLM 获取 schema 上下文。根据 schema 大小自动选择最佳策略：小型 schema 返回完整纯文本，大型 schema 使用嵌入搜索。

使用搜索策略时，可选的 `--type` 和 `--model` 过滤器可以缩小结果范围。

```bash
janus memory fetch -q "customer order price"
janus memory fetch -q "revenue" --type column --model orders
janus memory fetch -q "日期" --threshold 50000 --output json
```

| 标志 | 说明 |
|------|------|
| `-q, --query` | 搜索查询（必填） |
| `--mdl` | MDL JSON 文件路径 |
| `-l, --limit` | 搜索策略的最大结果数（默认：5） |
| `-t, --type` | 过滤：`model`、`column`、`relationship`、`view`（仅搜索策略） |
| `--model` | 按模型名称过滤（仅搜索策略） |
| `--threshold` | 完整策略与搜索策略之间的字符阈值（默认：30,000） |
| `-o, --output` | 输出格式：`table`（默认）、`json` |

### `janus memory store`

存储一个自然语言到 SQL 的配对，供将来的 few-shot 检索使用。

```bash
janus memory store \
  --nl "show top customers by revenue" \
  --sql "SELECT c_name, sum(o_totalprice) FROM orders JOIN customer GROUP BY 1 ORDER BY 2 DESC" \
  --datasource postgres
```

### `janus memory recall`

按语义相似度搜索已存储的 NL→SQL 配对。

```bash
janus memory recall -q "best customers"
janus memory recall -q "月度營收" --datasource mysql --limit 5 --output json
```

| 标志 | 说明 |
|------|------|
| `-q, --query` | 搜索查询（必填） |
| `-l, --limit` | 最大结果数（默认：3） |
| `-d, --datasource` | 按数据源过滤 |
| `-o, --output` | 输出格式：`table`（默认）、`json` |

### `janus memory status`

显示索引统计信息：存储路径、表名和行数。

```bash
janus memory status
# Path: /Users/you/.janus/memory
#   schema_items: 47 rows
#   query_history: 12 rows
```

### `janus memory reset`

删除所有 memory 表并重新开始。

```bash
janus memory reset          # prompts for confirmation
janus memory reset --force  # skip confirmation
```

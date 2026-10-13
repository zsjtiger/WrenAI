# janus-pydantic

Janus AI 的 Pydantic AI 集成。将由 CLI 准备好的 Janus 项目作为工具包挂载到你的智能体上，由上下文层负责 Schema 解析、记忆召回和 SQL 执行。

**何时使用此 SDK**：当你要构建一个 [Pydantic AI](https://ai.pydantic.dev) 智能体，并需要针对 Janus 项目回答数据问题时。如果只是一次性的 CLI 使用，单独使用 `janus` 命令即可。

---

## 前置条件

> ⚠️ **注意：请先安装 Janus CLI。** 此 SDK 是对已由 `janus` CLI 准备好的 Janus 项目（profile + MDL + 可选的记忆索引）的轻量适配层。缺少这些内容时，`JanusToolkit.from_project()` 没有可挂载的对象，会在构造时失败。安装此包之前，请先按照[安装指南](https://docs.crossnow.cn/oss/get_started/installation)完成准备。

最小化的 CLI 引导流程：

```bash
janus profile add my_project --datasource postgres   # or mysql, duckdb, ...
janus context init
janus context set-profile my_project                  # binds profile to project
janus context build                                   # produces target/mdl.json
janus memory index                                    # optional but recommended
```

完整的 CLI 配置流程（包括 `.env` 配置，以及如何通过 `janus docs connection-info` 查看连接器字段）请参见[连接你的数据库](/oss/guides/connect)。

---

## 安装

选择与项目 `data_source` 相匹配的数据源附加项：

```bash
pip install "janus-pydantic[postgres,memory]"   # or mysql, bigquery, ...
```

| 附加项 | 用途 |
|---|---|
| `postgres` / `mysql` / `bigquery` / `snowflake` / `clickhouse` / `trino` / `mssql` / `databricks` / `redshift` / `spark` / `athena` / `oracle` | 数据源直通（DuckDB 无需附加项） |
| `memory` | 启用 3 个记忆工具（`janus_fetch_context`、`janus_recall_queries`、`janus_store_query`） |
| `all` | 同时启用所有数据源，适合实验；用于生产环境则较重 |

如果已经安装了 `janusai`（例如你在使用 CLI），只需执行 `pip install janus-pydantic`，你现有的附加项会自动沿用。

---

## 快速开始

```python
from janus_pydantic import JanusToolkit
from pydantic_ai import Agent

toolkit = JanusToolkit.from_project("./analytics_db")

agent = Agent(
    "openai:gpt-4o",
    instructions=toolkit.instructions(),
    toolsets=[toolkit.toolset()],
)

result = agent.run_sync("Top 5 customers by revenue last quarter?")
print(result.output)
```

工具包会读取项目的 MDL、连接 profile 和 `instructions.md`；指令字符串会教智能体推荐的工作流（召回 → 获取上下文 → 编写 SQL → 存储结果）。

---

## API 参考

### `JanusToolkit.from_project(path, *, profile=None)`

根据由 CLI 准备好的 Janus 项目目录构建工具包。

| 参数 | 类型 | 说明 |
|---|---|---|
| `path` | `str \| Path` | 项目根目录（包含 `janus_project.yml` 的目录） |
| `profile` | `str \| None` | 可选的 profile 名称。解析顺序：此关键字参数 → `janus_project.yml` 中的 `profile:` 字段 → 全局激活的 profile |

记忆工具会被自动检测：如果存在 `<path>/.janus/memory/`，则会在 3 个运行时工具之外额外暴露 3 个记忆工具；如果不存在，则只有运行时工具。

### `toolkit.toolset(*, include_memory_write=True, takes_ctx=False)`

返回绑定到此工具包的 Pydantic AI `FunctionToolset`。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `include_memory_write` | `True` | 设为 `False` 可将记忆设为只读（去掉 `janus_store_query`） |
| `takes_ctx` | `False` | 设为 `True` 可将 `ctx: RunContext` 作为每个工具的第一个参数注入，用于与带 `deps_type=` 类型的工具混用 |

返回一个 `FunctionToolset`，包含 3 个运行时工具，加上 0、2 或 3 个记忆工具，具体数量取决于记忆状态和 `include_memory_write`。

### `toolkit.instructions(*, toolset=None)`

感知 Janus 的指令字符串，会根据已启用的工具进行调整，并在存在时包含项目的 `instructions.md`。如果你自定义了传给 `Agent` 的 `toolset`（例如设置了 `include_memory_write=False`），请向这里传入同一个 `toolset`，这样工作流会去掉持久化步骤，而不会指示智能体调用一个并不存在的工具。

### 工具（面向 LLM）

| 工具 | 返回值 | 用途 |
|---|---|---|
| `janus_query` | `JanusQueryResult` | 通过 Janus 的上下文层执行 SQL；上限 1000 行 |
| `janus_dry_plan` | `str` | 规划 SQL 但不执行；校验其是否正确指向 MDL 模型 |
| `janus_list_models` | `list[ModelSummary]` | 列出项目模型，包括列数和描述 |
| `janus_fetch_context` | `FetchContextResult` | 针对一个自然语言问题检索 Schema 和业务上下文 |
| `janus_recall_queries` | `list[RecalledPair]` | 返回相似的历史 NL→SQL 配对，作为少样本示例 |
| `janus_store_query` | `str` | 持久化已确认的 NL→SQL 配对（注册时 `retries=0`，写入失败不会循环重试） |

每个工具都以 `retries=2` 注册，因此 LLM 有两次机会自行修正 SQL 或元数据错误。被归类为基础设施错误（连接失败、文件缺失）的错误会以 `JanusError` 的形式抛出，而不会转换为 `ModelRetry`。

### 直接 Python API

当你希望在智能体循环之外调用 Janus 时：

```python
toolkit.query("SELECT ...")            # → pyarrow.Table
toolkit.dry_plan("SELECT ...")          # → str (target-dialect SQL)
toolkit.dry_run("SELECT ...")           # → None (validates without execution)

toolkit.memory.fetch("revenue trends")
toolkit.memory.recall("top customers", limit=3)
toolkit.memory.store(nl="...", sql="...", tags=["revenue"])
```

仅提供同步接口，没有 `aquery` / `afetch` 变体。底层引擎使用同步 I/O；Pydantic AI 会自动将同步工具桥接到其异步运行循环中，因此用 `asyncio.to_thread` 包装它们只是伪异步，并不会带来真正的并发收益。待 Janus AI 发布原生异步引擎后再重新评估。

---

## 集成模式

### 通过 `output_type=` 获取结构化输出

Pydantic AI 的核心特性：要求模型以类型化的 Pydantic 实例返回答案，并由框架进行校验。它与我们的工具集开箱即用：

```python
from pydantic import BaseModel

class TopCustomers(BaseModel):
    period: str
    customers: list[str]

agent = Agent(
    "openai:gpt-4o",
    instructions=toolkit.instructions(),
    toolsets=[toolkit.toolset()],
    output_type=TopCustomers,    # ← framework validates output into this type
)
result = agent.run_sync("Top 5 customers last quarter?")
print(result.output.customers)  # already a list[str], no parsing needed
```

可运行版本参见 [`examples/pydantic_ai_structured_demo.py`](https://github.com/CrossNow/JanusAI/blob/main/sdk/janus-pydantic/examples/pydantic_ai_structured_demo.py)。

### 只读记忆（共享 / 精选项目）

当智能体应当从过去的查询中学习，但不应污染记忆存储时，请使用 `include_memory_write=False`：

```python
toolset = toolkit.toolset(include_memory_write=False)
agent = Agent(
    "openai:gpt-4o",
    instructions=toolkit.instructions(toolset=toolset),  # keep prompt in sync
    toolsets=[toolset],
)
```

向 `instructions()` 传入 `toolset=`，可确保工作流去掉"存储查询"这一步，而不会指示智能体调用一个已经不存在的工具。

### 与 `deps_type=` 工具混用

当你希望在同一个智能体中，把 Janus 工具与你自己的依赖注入工具结合使用时，请启用 `takes_ctx=True`：

```python
@dataclass
class MyDeps:
    api_client: ApiClient

agent = Agent(
    "openai:gpt-4o",
    deps_type=MyDeps,
    toolsets=[toolkit.toolset(takes_ctx=True)],   # ← required when deps_type is set
)

# Your own tool that uses deps:
@agent.tool
def lookup_external(ctx: RunContext[MyDeps], id: str) -> str:
    return ctx.deps.api_client.fetch(id)
```

Janus 工具在内部会忽略上下文（工具包自身保存状态）。`takes_ctx=True` 只是添加了该参数，使函数签名与 Pydantic AI 基于 deps 类型的注册方式兼容。

### 多个项目，一个程序

一个工具包只绑定一个项目。要查询多个 Janus 项目，请分别构建多个工具包，并在 Python 中协调：

```python
loans = JanusToolkit.from_project("./loans_proj")
events = JanusToolkit.from_project("./events_proj")

loans_agent = Agent(model=..., toolsets=[loans.toolset()], instructions=loans.instructions())
events_agent = Agent(model=..., toolsets=[events.toolset()], instructions=events.instructions())
```

跨项目的 join 必须在 Python 中完成，而不能在 SQL 中完成，因为每个项目都有自己的 MDL 和连接。

---

## 故障排查

| 现象 | 原因 | 修复方法 |
|---|---|---|
| 在 SQL_PLANNING 阶段出现 `table 'janus.<schema>.<x>' not found` | 智能体写成了 `schema.table`，而不是 MDL 模型名 | 收紧指令，禁止使用物理名称；或让智能体先调用 `janus_list_models` |
| 连接指向了错误的数据库 | 项目没有 `profile:` 固定配置，回退到了全局激活的 profile | 运行 `janus context set-profile <name>` 固定绑定 |
| `MissingSecretError` | profile 中的 `${VAR}` 未被解析 | 在 `<project>/.env` 中填写对应的键 |
| `janus_query` 返回的行数被截断 | 每次工具调用的硬上限为 1000 行 | 在 SQL 中添加 `LIMIT`，或对更大的数据量使用直接 API（`toolkit.query`） |

---

## 兼容性

| `janus-pydantic` | `janusai` | `pydantic-ai` |
|---|---|---|
| 0.1.x | >= 0.7.0 | >= 1.0, < 2.0 |

---

## 限制

- **仅提供同步直接 API。** 原因见 API 参考。
- **每个智能体一个工具包。** 对于多个 Janus 项目，请分别构建工具包和智能体，并在 Python 中协调。
- **无热重载。** `target/mdl.json` 会在每次工具调用时重新读取，因此 `janus context build` 的更新会实时生效；但更改 profile 需要构建新的工具包。
- **不要在智能体正在使用同一项目时运行 `janus memory index`。** 索引操作会删除并重建 LanceDB 的 Schema 表，并发读取可能会暂时失败。

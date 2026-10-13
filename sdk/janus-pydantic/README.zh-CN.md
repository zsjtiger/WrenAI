# janus-pydantic

🌐 [English](./README.md) · **简体中文**

[Janus AI Core](https://github.com/CrossNow/JanusAI) 的 Pydantic AI 集成。

只需三行代码，即可把由 CLI 准备好的 Janus 项目接入 Pydantic AI agent：

```python
from janus_pydantic import JanusToolkit
from pydantic_ai import Agent

toolkit = JanusToolkit.from_project("./analytics_db")
agent = Agent(
    "openai:gpt-4o",
    instructions=toolkit.instructions(),
    toolsets=[toolkit.toolset()],
)
result = agent.run_sync("How many enterprise customers do we have?")
print(result.output)
```

> ⚠️ **需先安装 Janus CLI。** 本 SDK 是对一个已由 `janus` CLI 准备好的 Janus 项目（profile + MDL + 可选的 memory 索引）的轻量适配层。在安装本包之前，请先按照[安装指南](https://docs.crossnow.cn/oss/get_started/installation)完成 CLI 的安装。

可运行的示例：

- [`examples/pydantic_ai_demo.py`](./examples/pydantic_ai_demo.py) — 同步的三行快速入门。代码量最少，推荐作为入门起点。
- [`examples/pydantic_ai_structured_demo.py`](./examples/pydantic_ai_structured_demo.py) —
  结构相同，但使用 `output_type=` 获得结构化、经过校验的 agent 输出。

## 前置条件

本包假设你已经使用 Janus CLI 准备好了项目：

```bash
janus profile add my_project --datasource duckdb   # 或 mysql、postgres 等
janus context init
janus context set-profile my_project               # 将 profile 绑定到项目
janus context build                                # 生成 target/mdl.json
janus memory index                                 # 可选，但推荐
```

如果还没有安装 CLI，请先安装 `janusai`：

```bash
pip install "janusai[memory,postgres]"
```

## 安装

`janus-pydantic` 提供了数据源和 memory 的 extra，它们会透传到对应的 `janusai` extra，因此只需安装一次：

```bash
# 与 janus_project.yml 所使用的数据源保持一致（DuckDB 无需额外 extra）：
pip install "janus-pydantic[mysql]"
pip install "janus-pydantic[postgres,memory]"
pip install "janus-pydantic[bigquery,memory]"

# 可用的数据源 extra：postgres, mysql, bigquery, snowflake,
# clickhouse, trino, mssql, databricks, redshift, spark, athena, oracle。

# `memory` extra 启用三个 memory 工具（janus_fetch_context、
# janus_recall_queries、janus_store_query）。若不安装，toolkit 只暴露
# 三个运行时工具。

# 为了实验而安装全部内容：
pip install "janus-pydantic[all,memory]"
```

如果已经安装了 `janusai`（例如你在使用 CLI），裸的 `pip install janus-pydantic` 即可——你已有的 extra 会照常生效。

## 你将获得什么

`JanusToolkit.from_project(path)` 提供以下能力：

- **6 个面向 LLM 的工具**（3 个运行时工具；当 `.janus/memory/` 存在时另有 3 个 memory 工具）：
  - `janus_query` — 通过 Janus 的语义层执行 SQL，返回类型化的 Pydantic 模型 `JanusQueryResult`
  - `janus_dry_plan` — 只规划 SQL 而不执行；验证其是否正确指向 MDL 模型
  - `janus_list_models` — 列出项目中的模型，包括列数与描述
  - `janus_fetch_context` — 为某个问题检索 schema 与业务上下文
  - `janus_recall_queries` — 召回相似的历史 NL→SQL 对，作为 few-shot 示例
  - `janus_store_query` — 持久化已确认的 NL→SQL 对，供日后召回（`retries=0`——写入失败不会循环重试）
- **Python 直接 API**（同步；不提供异步包装，原因见 `docs/core/sdk/pydantic.md`）：
  ```python
  toolkit.query("SELECT ...")              # → pyarrow.Table
  toolkit.dry_plan("SELECT ...")            # → str（目标方言的 SQL）
  toolkit.dry_run("SELECT ...")             # → None（只校验，不执行）
  toolkit.memory.fetch("revenue trends")
  toolkit.memory.recall("top customers")
  toolkit.memory.store(nl="...", sql="...", tags=["..."])
  ```
- **`toolkit.instructions()`** — Pydantic AI 感知的 instructions 字符串，会根据已启用的工具进行调整；若项目中存在 `instructions.md`，还会将其包含在内。

引擎返回的错误会被转换为 Pydantic AI 的 `ModelRetry`，并附带按阶段区分的说明——agent 可以自行纠正 SQL 或元数据错误。基础设施错误（连接失败、DuckDB 文件缺失）则会以 `JanusError` 抛出，交由外层代码处理。

## 配置

```python
JanusToolkit.from_project(
    path,                # 必填——已准备好的 Janus 项目路径
    profile="prod",      # 可选——选择一个命名的 profile（默认：active）
)

toolkit.toolset(
    include_memory_write=True,   # 设为 False 可使 memory 保持只读
    takes_ctx=False,             # 若与 deps_type= 工具混用，设为 True
)

toolkit.instructions(toolset=toolset)  # 传入同一个 toolset，以保持 prompt 同步
```

Memory 会**自动检测**：项目中若存在 `<path>/.janus/memory/`，则在 3 个运行时工具之外，同时暴露 3 个 memory 工具；若不存在，则只有运行时工具。要启用，请在项目根目录运行 `janus memory index`；要禁用，删除该目录即可。没有用于覆盖的参数。

`include_memory_write=False` 会从 toolset 中移除 `janus_store_query`，同时保留 `janus_fetch_context` 与 `janus_recall_queries`。适用于共享的或经过整理的 memory 存储。

`takes_ctx=True` 会让每个工具的第一个参数都为 `ctx: RunContext`。当你在同一个 agent 中混用 janus 工具与你自己带 `deps_type=` 的工具时使用。该 context 在内部会被忽略——toolkit 已经自行保存了状态。

## 兼容性矩阵

| `janus-pydantic` | `janusai` | `pydantic-ai` |
|---|---|---|
| 0.1.x | >= 0.7.0 | >= 1.0, < 2.0 |

## 已知限制（v0.1）

- **仅提供同步直接 API。** 未提供 `aquery` / `adry_plan` 等方法——Pydantic AI 会自动将同步工具桥接到其异步运行循环中，而底层 `JanusEngine` 是同步 I/O，因此异步包装只是“假异步”，并不会带来真正的并发收益。待 Core 发布原生异步引擎后再行评估。
- **每个 agent 只能有一个 toolkit。** 如果需要查询多个 Janus 项目，请分别构建 toolkit 与 agent，并在 Python 中进行联合查询。
- **Memory 自动检测**，自 `.janus/memory/` 判断，且没有覆盖用的参数。要启用，请运行 `janus memory index`；要禁用，删除该目录。
- **没有热重载机制。** 每次工具调用都会重新读取 `target/mdl.json`，因此 `janus context build` 的更新会被自动读取。修改 profile 则需要重新构造 toolkit。
- **不要在 agent 正在使用同一项目时运行 `janus memory index`。** 该操作会删除并重建 LanceDB schema 表，并发读取可能会短暂失败。


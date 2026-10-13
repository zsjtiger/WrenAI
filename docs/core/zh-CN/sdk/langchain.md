# janus-langchain

Janus AI 的 LangChain 与 LangGraph 集成。将由 CLI 准备好的 Janus 项目作为工具包挂载到你的智能体上，由上下文层负责 Schema 解析、记忆召回和 SQL 执行。

**何时使用此 SDK**：当你要构建一个 LangChain 或 LangGraph 智能体，并需要针对 Janus 项目回答数据问题时。如果只是一次性的 CLI 使用，单独使用 `janus` 命令即可。

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

---

## 安装

选择与项目 `data_source` 相匹配的数据源附加项：

```bash
pip install "janus-langchain[postgres,memory]"   # or mysql, bigquery, ...
```

| 附加项 | 用途 |
|---|---|
| `postgres` / `mysql` / `bigquery` / `snowflake` / `clickhouse` / `trino` / `mssql` / `databricks` / `redshift` / `spark` / `athena` / `oracle` | 数据源直通（DuckDB 无需附加项） |
| `memory` | 启用 3 个记忆工具（`janus_fetch_context`、`janus_recall_queries`、`janus_store_query`） |
| `all` | 同时启用所有数据源，适合实验；用于生产环境则较重 |

如果已经安装了 `janusai`（例如你在使用 CLI），只需执行 `pip install janus-langchain`，你现有的附加项会自动沿用。

---

## 快速开始

```python
from janus_langchain import JanusToolkit
from langchain.agents import create_agent

toolkit = JanusToolkit.from_project("<path_to_project>")

agent = create_agent(
    model="openai:gpt-4o",
    tools=toolkit.get_tools(),
    system_prompt=toolkit.system_prompt(),
)

result = agent.invoke({"messages": [
    {"role": "user", "content": "Top 5 customers by revenue last quarter?"}
]})
print(result["messages"][-1].content)
```

就是这样。工具包会读取项目的 MDL、连接 profile 和 `instructions.md`；系统提示词会教智能体推荐的工作流（获取上下文 → 召回相似查询 → 编写 SQL → 存储结果）。

---

## API 参考

### `JanusToolkit.from_project(path, *, profile=None)`

根据由 CLI 准备好的 Janus 项目目录构建工具包。

| 参数 | 类型 | 说明 |
|---|---|---|
| `path` | `str \| Path` | 项目根目录（包含 `janus_project.yml` 的目录） |
| `profile` | `str \| None` | 可选的 profile 名称。解析顺序：此关键字参数 → `janus_project.yml` 中的 `profile:` 字段 → 全局激活的 profile |

记忆工具会被自动检测：如果存在 `<path>/.janus/memory/`，则会在 3 个运行时工具之外额外暴露 3 个记忆工具；如果不存在，则只有运行时工具。

### `toolkit.get_tools(*, include_memory_write=True, raise_on_error=False)`

返回绑定到此工具包的 LangChain 兼容工具。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `include_memory_write` | `True` | 设为 `False` 可将记忆设为只读（去掉 `janus_store_query`） |
| `raise_on_error` | `False` | 设为 `True` 可将异常交给 LangChain 的重试逻辑处理，而不是返回错误信封 |

返回值：3 个运行时工具，加上 0、2 或 3 个记忆工具的列表，具体数量取决于记忆状态和 `include_memory_write`。

### `toolkit.system_prompt(*, tools=None)`

感知 Janus 的系统提示词，会根据已启用的工具进行调整，并在存在时包含项目的 `instructions.md`。如果你自定义了传给 `create_agent` 的 `tools` 列表（例如设置了 `include_memory_write=False`），请向这里传入同一个 `tools` 列表，这样工作流会去掉持久化步骤，而不会指示智能体调用一个并不存在的工具。

### 工具（面向 LLM）

| 工具 | 用途 |
|---|---|
| `janus_query` | 通过 Janus 的上下文层执行 SQL；返回行数据（上限 1000 行） |
| `janus_dry_plan` | 规划 SQL 但不执行；校验其是否正确指向 MDL 模型 |
| `janus_list_models` | 列出项目模型，包括列数和描述 |
| `janus_fetch_context` | 针对一个自然语言问题检索 Schema 和业务上下文 |
| `janus_recall_queries` | 返回相似的历史 NL→SQL 配对，作为少样本示例 |
| `janus_store_query` | 持久化已确认的 NL→SQL 配对，供以后召回 |

### 直接 Python API

当你希望在智能体循环之外调用 Janus 时：

```python
toolkit.query("SELECT ...")           # → pyarrow.Table
toolkit.dry_plan("SELECT ...")        # → str (target-dialect SQL)
toolkit.dry_run("SELECT ...")         # → None (validates without execution)

toolkit.memory.fetch("revenue trends")
toolkit.memory.recall("top customers", limit=3)
toolkit.memory.store(nl="...", sql="...", tags=["revenue"])
```

---

## 集成模式

### 只读记忆（共享 / 精选项目）

当你希望智能体从过去的查询中学习，但不希望污染记忆存储时，请使用 `include_memory_write=False`：

```python
tools = toolkit.get_tools(include_memory_write=False)
agent = create_agent(
    model="openai:gpt-4o",
    tools=tools,
    system_prompt=toolkit.system_prompt(tools=tools),  # important: keep prompt in sync
)
```

向 `system_prompt()` 传入 `tools=`，可确保工作流去掉"存储查询"这一步，而不会指示智能体调用一个已经不存在的工具。

### LangGraph 自定义循环

当你需要自定义路由、状态或流式输出时，可以用 LangGraph 原语构建 ReAct 循环：

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain.chat_models import init_chat_model

tools = toolkit.get_tools()
llm = init_chat_model("openai:gpt-4o").bind_tools(tools)

def chatbot(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}

graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", tools_condition)
graph.add_edge("tools", "chatbot")
app = graph.compile()
```

可运行版本参见 [`examples/langgraph_demo.py`](https://github.com/CrossNow/JanusAI/blob/main/sdk/janus-langchain/examples/langgraph_demo.py)。

### 多个项目，一个程序

一个工具包只绑定一个项目。要查询多个 Janus 项目，请分别构建多个工具包，并用 Python 在它们之间协调：

```python
loans = JanusToolkit.from_project("./loans_proj")
events = JanusToolkit.from_project("./events_proj")

# Two agents, each scoped to its own project's tools / memory.
loans_agent = create_agent(model=..., tools=loans.get_tools(), system_prompt=loans.system_prompt())
events_agent = create_agent(model=..., tools=events.get_tools(), system_prompt=events.system_prompt())

# Federate in Python — pass IDs / aggregates between agents.
```

跨项目的 join 必须在 Python 中完成，而不能在 SQL 中完成，因为每个项目都有自己的 MDL 和连接。

---

## 故障排查

| 现象 | 原因 | 修复方法 |
|---|---|---|
| 在 SQL_PLANNING 阶段出现 `table 'janus.<schema>.<x>' not found` | 智能体写成了 `schema.table`，而不是 MDL 模型名 | 收紧系统提示词，禁止使用物理名称；或先调用 `janus_list_models` |
| 连接指向了错误的数据库 | 项目没有 `profile:` 固定配置，回退到了全局激活的 profile | 运行 `janus context set-profile <name>` 固定绑定 |
| `MissingSecretError` | profile 中的 `${VAR}` 未被解析 | 在 `<project>/.env` 中填写对应的键 |
| `janus_query` 返回的行数被截断 | 每次工具调用的硬上限为 1000 行 | 在 SQL 中添加 `LIMIT`，或对更大的数据量使用直接 API（`toolkit.query`） |

---

## 兼容性

| `janus-langchain` | `janusai` | `langchain` | `langgraph` |
|---|---|---|---|
| 0.2.x | >= 0.7.0 | >= 1.0 | >= 1.0 |

---

## 限制

- **仅支持同步工具。** 当工具在异步 LangGraph 中运行时，LangChain 会自动桥接到线程池；服务超过 32 个并发用户的多租户服务器可能会耗尽默认执行器。
- **每个智能体一个工具包。** 对于多个 Janus 项目，请分别构建工具包和智能体，并在 Python 中协调。
- **无热重载。** `target/mdl.json` 会在每次工具调用时重新读取，因此 `janus context build` 的更新会实时生效；但更改 profile 需要构建新的工具包。
- **不要在智能体正在使用同一项目时运行 `janus memory index`。** 索引操作会删除并重建 LanceDB 的 Schema 表，并发读取可能会暂时失败。

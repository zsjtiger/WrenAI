# janus-langchain

🌐 [English](./README.md) · **简体中文**

[Janus AI Core](https://github.com/CrossNow/JanusAI) 的 LangChain 与 LangGraph 集成。

只需三行代码，即可把由 CLI 准备好的 Janus 项目接入 LangChain agent：

```python
from janus_langchain import JanusToolkit
from langchain.agents import create_agent

toolkit = JanusToolkit.from_project("./analytics_db")
agent = create_agent(
    model="openai:gpt-4o",
    tools=toolkit.get_tools(),
    system_prompt=toolkit.system_prompt(),
)
```

完整的可运行示例：

- [`examples/langchain_demo.py`](./examples/langchain_demo.py) — 使用 ``langchain.agents.create_agent``，即高层工厂函数。代码量最少，推荐作为入门起点。
- [`examples/langgraph_demo.py`](./examples/langgraph_demo.py) — 基于 LangGraph 原语（`StateGraph` + `ToolNode` + 条件边）构建 ReAct 循环。需要自定义路由、状态或流式输出时使用。

## 前置条件

本包假设你已经使用 Janus CLI 准备好了项目：

```bash
janus context init
janus context build
janus memory index   # 可选，但推荐
janus profile add ...
```

如果还没有安装 CLI，请先安装 `janusai`：

```bash
pip install "janusai[memory,postgres]"
```

## 安装

`janus-langchain` 提供了数据源和 memory 的 extra，它们会透传到对应的 `janusai` extra，因此只需安装一次：

```bash
# 与 janus_project.yml 所使用的数据源保持一致（DuckDB 无需额外 extra）：
pip install "janus-langchain[mysql]"
pip install "janus-langchain[postgres,memory]"
pip install "janus-langchain[bigquery,memory]"

# 可用的数据源 extra：postgres, mysql, bigquery, snowflake,
# clickhouse, trino, mssql, databricks, redshift, spark, athena, oracle。

# `memory` extra 启用三个 memory 工具（janus_fetch_context、
# janus_recall_queries、janus_store_query）。若不安装，toolkit 只暴露
# 三个运行时工具。

# 为了实验而安装全部内容：
pip install "janus-langchain[all,memory]"
```

如果你更喜欢单独安装 `janusai`（例如你已经在使用 CLI），裸包即可，你已有的 `janusai` extra 会照常生效：

```bash
pip install janus-langchain
```

## 你将获得什么

`JanusToolkit.from_project(path)` 提供以下能力：

- **6 个面向 LLM 的工具**（3 个运行时工具；当 `.janus/memory/` 存在时另有 3 个 memory 工具）：
  - `janus_query` — 通过 Janus 的上下文层执行 SQL，返回行数据
  - `janus_dry_plan` — 只规划 SQL 而不执行，用于验证其是否正确指向目标模型
  - `janus_list_models` — 列出项目中的模型，包括列数与描述
  - `janus_fetch_context` — 为某个问题检索相关的 schema 与业务上下文
  - `janus_recall_queries` — 召回相似的历史 NL→SQL 对，作为 few-shot 示例
  - `janus_store_query` — 持久化已确认的 NL→SQL 对，供日后召回
- **Python 直接 API**：
  ```python
  toolkit.query("SELECT ...")             # → pyarrow.Table
  toolkit.dry_plan("SELECT ...")           # → str（目标方言的 SQL）
  toolkit.dry_run("SELECT ...")            # → None（仅校验）
  toolkit.memory.fetch("revenue trends")
  toolkit.memory.recall("top customers")
  toolkit.memory.store(nl="...", sql="...", tags=["..."])
  ```
- **`toolkit.system_prompt()`** — 感知 Janus 的系统提示词，会根据已启用的工具进行调整；若项目中存在 `instructions.md`，还会将其包含在内。

## 配置

```python
JanusToolkit.from_project(
    path,                # 必填——已准备好的 Janus 项目路径
    profile="prod",      # 可选——选择一个命名的 profile（默认：active）
)

toolkit.get_tools(
    include_memory_write=True,   # 设为 False 可使 memory 保持只读
    raise_on_error=False,        # 设为 True 可将异常抛给 LangChain 重试
)
```

Memory 会**自动检测**：项目中若存在 `<path>/.janus/memory/`，则在 3 个运行时工具之外，同时暴露 3 个 memory 工具；若不存在，则只有运行时工具。要启用，请在项目根目录运行 `janus memory index`；要禁用，删除该目录即可。没有用于覆盖的参数。

`include_memory_write=False` 会从返回列表中移除 `janus_store_query`，同时保留 `janus_fetch_context` 与 `janus_recall_queries`。当你希望 agent 只读取经过整理的历史问答对、而从不写入新记录时使用（例如共享的或固定的 memory）。若 memory 未启用，此参数无任何作用——无论如何都不会返回 memory 工具。

### `path`、`profile` 与 `.env` 如何协同工作

有三类状态共同决定连接。弄清每一项各自负责什么，可以避免意外：

| 来源 | 保存内容 | 由谁解析 |
|---|---|---|
| `path/janus_project.yml` + `target/mdl.json` | MDL 模型、schema、`data_source` | `from_project(path)` |
| `path/.env` | 敏感值（`MYSQL_HOST`、`MYSQL_PASSWORD`、…） | `from_project(path)` 自动加载 |
| `~/.janus/profiles.yml` | 连接模板（`host: ${MYSQL_HOST}`、…） | `profile=` 参数或回退链 |

**`profile=` 解析链**（优先级从高到低）：

1. 传给 `from_project` 的显式参数 `profile="<name>"`。
2. 项目 `janus_project.yml` 中的 `profile:` 字段，例如：
   ```yaml
   schema_version: 3
   data_source: mysql
   profile: test-project3   # 将本项目锁定到指定的 profile
   ```
3. 全局激活的 profile（`janus profile switch <name>`）。

### `profile=` 何时真正改变所连接的数据库？

这一点比较微妙，因为 **profile 的值是从项目的 `.env` 中解析的模板**，而不是独立的连接记录。下面是三种情况：

**场景 A — `profile=` 不起作用（最常见）**

你的 `~/.janus/profiles.yml` 中有多个 profile，它们都使用相同的占位符名称：

```yaml
profiles:
  test-project3:
    datasource: mysql
    host: ${MYSQL_HOST}
    database: ${MYSQL_DATABASE}
  test-project4:
    datasource: mysql
    host: ${MYSQL_HOST}        # ← 相同的占位符
    database: ${MYSQL_DATABASE}
```

由于 `from_project("/path/to/test-project3")` 会把 `test-project3/.env` 加载到环境变量中，**两个 profile 会解析为同一个连接**——`${MYSQL_HOST}` 总是读取 project3 的 `.env`，与你选择的 profile 名称无关。在这种布局下，profile 的选择只是名义上的。

**场景 B — `profile=` 选择不同的占位符**

```yaml
profiles:
  dev:
    host: ${DEV_HOST}
  prod:
    host: ${PROD_HOST}
```

现在 `profile="dev"` 与 `profile="prod"` 会从同一个 `.env` 中读取不同的环境变量，因此选择会产生影响。

**场景 C — `profile=` 选择硬编码的值或不同的数据源**

```yaml
profiles:
  local:
    datasource: duckdb
    url: /tmp/local.duckdb
    format: duckdb
  remote:
    datasource: postgres
    host: prod-db.example.com   # 硬编码
    port: 5432
```

`profile="local"` 与 `profile="remote"` 确实连接到不同的数据库。注意：如果 `janus_project.yml` 指定了 `data_source:`，而你选择的 profile 使用了不同的 `datasource:`，连接将失败——项目的 MDL 是针对某一种特定方言构建的。

### 建议：一个项目，一个 profile

如果你采用常见模式，即**每个数据库对应一个 Janus 项目**（每个项目有自己的 `.env`，并指向自己的数据库），那么请在 `janus_project.yml` 中设置 profile，并且不再传入 `profile=`：

```yaml
# janus_project.yml
schema_version: 3
name: test-project3
data_source: mysql
profile: test-project3
```

```python
toolkit = JanusToolkit.from_project("/path/to/test-project3")
```

这样即可把项目固定到其预期的 profile，不必再纠结“当前激活的 profile 是不是我以为的那个？”，而且在同一台机器上执行 `janus profile switch` 时也不会受影响。

## 兼容性矩阵

| `janus-langchain` | `janusai` | `langchain` | `langgraph` |
|---|---|---|---|
| 0.1.0 | >= 0.7.0 | >= 1.0 | >= 1.0 |

## 已知限制（v0.1）

- **仅支持同步工具。** 在异步 LangGraph 中运行工具时，LangChain 会自动桥接到线程池；服务于超过约 32 个并发用户的多租户服务器，可能会耗尽默认的执行器线程池。
- **每个 agent 只能有一个 toolkit。** 如果需要查询多个 Janus 项目，请分别构建 agent。
- **Memory 自动检测**，自 `.janus/memory/` 判断，且没有覆盖用的参数。要启用，请运行 `janus memory index`；要禁用，删除该目录。
- **没有热重载机制。** 每次工具调用都会重新读取 `target/mdl.json`，因此 CLI 执行 `janus context build` 后的更新会被自动读取。修改 profile 则需要重新构造 toolkit。
- **不要在 agent 正在使用同一项目时运行 `janus memory index`。** 该操作会删除并重建 LanceDB schema 表，并发读取可能会短暂失败。


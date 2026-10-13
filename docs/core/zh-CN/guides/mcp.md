---
sidebar_label: 启动 MCP 服务器
---

# 启动 MCP 服务器

`janus serve mcp` 会把 Janus 项目的查询、Schema 和业务知识工具暴露给任何 MCP 客户端，例如 Claude Desktop、Claude Code、Cursor 或其他 IDE。服务器在进程内基于编译好的 MDL 和当前激活的连接配置文件运行，没有独立的后端，只需要你已经安装的 CLI。

## 开始之前

- 一个已构建 `target/mdl.json` 的 Janus 项目（`janus context build`）。
- 已绑定的连接配置文件（`janus profile add` / `janus context set-profile`），除非你只需要 Schema 和转译工具（`--no-connect`）。
- `mcp` 扩展：`pip install 'janusai[mcp]'`（如果在 `core/janus` 源码检出中工作，则运行 `just install-extra mcp`）。

## 启动服务器

```bash
cd my-project
janus serve mcp
```

默认以 `stdio` 模式运行，这是通过子进程启动 `janus` 的客户端所期望的模式。如果要为其他工具提供本地服务器连接，请使用 `--transport http`：

```bash
janus serve mcp --transport http --host 127.0.0.1 --port 8080
```

添加 `--allow-write` 可以启用 `store_query`（默认关闭，服务器默认只读）；添加 `--no-connect` 则启动只做转译、从不访问数据库的服务器（此时 `run_sql` / `dry_run` / `query_cube` 会被禁用）。

启动时服务器会为你刚才的调用方式打印可直接复制的注册命令：HTTP 模式为 `claude mcp add` / `codex mcp add` 命令，stdio 模式则会额外给出 JSON 格式的 `mcpServers` 配置块。传入 `--quiet` 可以关闭这些输出。

## 接入客户端

启动横幅已经为你的项目填好了下面的命令，本节解释这些配置的含义。大多数桌面端或 IDE 的 MCP 客户端使用 JSON 配置，并通过 stdio 启动服务器：

```json
{
  "mcpServers": {
    "janus": {
      "command": "janus",
      "args": ["serve", "mcp"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

`cwd` 必须位于项目目录内（或者在 `args` 中改为传入 `--project /path/to/project`）。添加配置后需要重启客户端。

如果是供其他机器或进程连接的服务器，请运行 `janus serve mcp --transport http --port 8080`，然后让客户端连接该主机和端口上的 Streamable HTTP 端点，而不是启动子进程。HTTP 默认绑定到 `127.0.0.1`，并且在当前版本中不提供 Bearer Token 认证，请保持只在本地使用。

## 客户端可以使用的内容

- **查询工具**：`run_sql`、`dry_run`、`dry_plan`、`query_cube`
- **Schema 工具**：`get_mdl`、`list_models`、`describe_model`、`get_data_source`、`list_cubes`、`describe_cube`、`list_functions`
- **知识工具**：`get_instructions`、`recall_queries`、`get_context`、`describe_schema`、`list_stored_queries`、`list_knowledge`，以及（需要 `--allow-write`）`store_query`
- **资源**：`janus://mdl`、`janus://instructions`、`janus://project`、`janus://agents`、`janus://knowledge/{path}`
- **提示词**：`janus_workflow`，一份现成的标准操作流程：Schema → 指令 → 检索 → dry-run → 运行 → 存储

`get_context` 和 `list_stored_queries` 在安装了 `memory` 扩展时会优先使用它（嵌入检索、完整查询历史），未安装时则回退到基于 `knowledge/` 的无依赖读取，这与 `recall_queries` 已有的降级方式一致。`describe_schema` 不需要任何额外扩展，它是 `get_mdl` 的纯文本版本，适合直接粘贴进 LLM 提示词。

每个参数和工具签名，请参见 [CLI 参考](/oss/reference/cli#janus-serve--mcp-server)。

## 安全说明

连接凭据在服务器启动时从配置文件中解析一次，并保留在服务器端，只有 SQL 文本、查询结果和元数据会穿过 MCP 边界。服务器从不自动构建 MDL：如果项目源文件比 `target/mdl.json` 更新，它会记录一条过期警告，但仍会继续使用现有 manifest，因此修改模型后需要重新运行 `janus context build`。

`janus://knowledge/{path}` 资源会在读取前解析请求的路径，并验证其仍位于项目的 `knowledge/` 目录内。会逃逸出该目录的路径（例如 `../janus_project.yml`）会被拒绝。

## 另请参阅

- [CLI 参考：`janus serve`](/oss/reference/cli#janus-serve--mcp-server)
- [管理项目](manage_project.md)：项目结构和 `target/mdl.json`（英文版）
- [连接你的数据库](connect.md)：为服务器查询所使用的配置文件进行设置

# SDK 与集成

Janus AI 以智能体为原生设计：同一个由 CLI 准备好的项目（MDL、`knowledge/`、记忆）可以通过多种访问模式驱动。无论你选择哪种模式，Schema 解析、记忆召回和受治理的 SQL 执行都来自同一个上下文层，因此每个智能体、脚本和应用都能获得同样可信的答案。

本页帮助你选择合适的访问模式。

## 我应该使用哪种访问模式？

| 如果你是…… | 使用 | 包 / 安装方式 |
|---|---|---|
| 在使用 **AI 编程智能体**（Claude Code、Cursor、Codex 等） | [技能](/oss/reference/skills)：智能体按需从 CLI 获取的工作流指南 | `npx skills add CrossNow/JanusAI` |
| 在**终端、脚本或 CI** 中自行查询 | [CLI](/oss/reference/cli)：直接进行规划、校验、执行和管理记忆 | PyPI 上的 `janusai` |
| 基于 **LangChain / LangGraph** 构建智能体 | [LangChain 工具包](./langchain.md)：将项目暴露为智能体工具 | PyPI 上的 `janus-langchain` |
| 基于 **Pydantic AI** 构建智能体 | [Pydantic AI 工具包](./pydantic.md)：将项目暴露为智能体工具 | PyPI 上的 `janus-pydantic` |
| 在**浏览器中**嵌入 MDL 感知的查询或 **CReport 仪表盘** | [WebAssembly 引擎](./wasm.md)：完全在客户端运行，无需服务器，也无需 CLI 引导 | npm 上的 `@janusai/janus-core-wasm` |

几条经验法则：

- **从技能 + CLI 开始。** 如果你日常主要使用编程智能体，只需安装一次，就能获得完整的工作流（搭建、丰富上下文、查询、存储），无需自行构建任何东西。
- **当你要构建自己的智能体或应用，并希望把 Janus 的上下文层作为工具包集成其中，而不是通过命令行调用 CLI 时，** 请选择框架 SDK。
- **当使用者是浏览器时，** 请选择 wasm。CReport 仪表盘在底层使用它，你也可以直接用它在客户端运行基于模型的 SQL。

## 各部分如何协同

框架 SDK 和 wasm 引擎并不取代 CLI，而是使用 CLI 所准备的项目。典型的分工如下：

1. **编写期（CLI + 技能）：** 连接 profile，搭建并丰富 MDL，构建 `target/mdl.json`，为记忆建立索引。
2. **运行期（从上述方式中任选其一）：** CLI、某个 SDK 工具包或 wasm 引擎基于编译好的上下文规划并执行查询。

所有模式共享的项目生命周期，请参见[管理项目](/oss/guides/manage_project)。

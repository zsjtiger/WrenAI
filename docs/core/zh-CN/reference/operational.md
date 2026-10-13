---
sidebar_label: 运维参考
---

# 运维参考

这是一页式的参考，列出了 Janus AI 使用的每一个路径、环境变量和发现规则。如果你需要在多台机器、多个环境或 CI 中运维 Janus AI，建议把本页加入书签。

## 文件系统布局

### 全局（`~/.janus/`）

| 路径 | 用途 | 创建者 |
|---|---|---|
| `~/.janus/profiles.yml` | 所有连接配置文件，以及 `active` 指针。权限：`0600`。 | `janus profile add` |
| `~/.janus/config.yml` | CLI 偏好设置。设置后包含 `default_project`。 | `janus context set-profile`、手动编辑 |
| `~/.janus/connection_info.json` | 旧版连接回退配置（为向后兼容而保留）。 | 较早的 CLI 版本 |
| `~/.janus/.env` | 用户全局的 `.env` 回退文件，用于 `${VAR}` 插值。 | 手动 |

可以通过 `JANUS_HOME` 覆盖整个全局目录。

### 项目级（`<project>/`）

| 路径 | 用途 | 是否提交 |
|---|---|---|
| `janus_project.yml` | 项目根配置、`schema_version` 锁定、绑定的配置文件和数据源。 | ✅ 是 |
| `models/<name>/metadata.yml` | 模型定义。 | ✅ 是 |
| `models/<name>/ref_sql.sql` | `ref_sql` 模型可选的独立 SQL 文件。 | ✅ 是 |
| `views/<name>/metadata.yml` | 视图定义。 | ✅ 是 |
| `views/<name>/sql.yml` | 视图可选的独立 `statement` 文件。 | ✅ 是 |
| `cubes/<name>/metadata.yml` | Cube 定义。 | ✅ 是 |
| `relationships.yml` | 所有关联关系。 | ✅ 是 |
| `knowledge/rules/` | 面向 LLM 的业务规则（取代 `instructions.md`）。 | ✅ 是 |
| `knowledge/sql/` | 经过确认的 NL→SQL 问答对，是记忆的事实来源。 | ✅ 是 |
| `knowledge/knowledge.yml` | knowledge 维度的 `schema_version`。 | ✅ 是 |
| `instructions.md` | 已弃用：请迁移到 `knowledge/rules/`（如存在仍会被读取）。 | ⚠️ 遗留 |
| `queries.yml` | 遗留的 NL-SQL 问答对，已被 `knowledge/sql/` 取代。 | ⚠️ 遗留 |
| `.env` | 项目级的 `.env`，用于 `${VAR}` 插值。 | ❌ 加入 gitignore |
| `.janus/memory/` | 派生的 LanceDB 索引（由 `knowledge/sql/` 重建）。 | ❌ 加入 gitignore |
| `target/mdl.json` | 编译后的 MDL manifest（可重建）。 | ❌ 加入 gitignore |

## 环境变量

| 变量 | 用途 | 默认值 |
|---|---|---|
| `JANUS_HOME` | 覆盖全局 Janus 目录。 | `~/.janus` |
| `JANUS_PROJECT_HOME` | 跳过向上查找项目的过程，直接指向项目根目录。 | —（从当前目录向上查找） |
| `OPENAI_API_KEY` | 记忆嵌入以及 `add-llms-md.js` 文档预构建所需。 | — |
| `CLAUDE_SKILLS_DIR` | 覆盖 `install.sh` 使用的 Skill 安装目录。 | `~/.claude/skills` |
| `JANUS_SKILLS_BRANCH` | 通过 curl 脚本安装 Skill 时覆盖使用的分支。 | `main` |

配置文件中的值也可以引用来自 `os.environ` 或 `.env` 文件的 `${VAR}`，参见[解析顺序](#env-resolution-order)。

## 项目发现

当 `janus` 命令需要项目（如 `query`、`memory fetch`、`context build` 等）时，CLI 会按以下顺序解析 `<project>`：

1. `--path <path>` 参数（显式指定）
2. `JANUS_PROJECT_HOME` 环境变量
3. 从当前目录向上查找 `janus_project.yml`
4. `~/.janus/config.yml` 中的 `default_project` 字段

如果找不到项目，CLI 会以清晰的错误退出，并提示运行 `janus context init` 或设置 `JANUS_PROJECT_HOME`。

## 配置文件解析

当命令需要连接时，CLI 会按以下顺序解析连接信息：

1. 显式的 `--connection-info '<json>'` 参数（优先级最高）
2. 显式的 `--connection-file <path>` 参数
3. `janus_project.yml` 中**绑定的配置文件**（`profile: <name>`）
4. `~/.janus/profiles.yml` 中的**激活配置文件**（`active` 指针）
5. 旧版的 `~/.janus/connection_info.json`

如果都找不到，命令会以连接错误失败。

## `.env` 解析顺序 {#env-resolution-order}

配置文件 YAML 中的 `${VAR}` 占位符会在建立连接时解析。CLI 会按以下顺序查找每个变量（第一个匹配者生效；进程环境变量优先于任何 `.env` 文件）：

1. `os.environ`：你在 Shell 中已经导出的变量
2. `$CWD/.env`：你运行 `janus` 的目录
3. `<project>/.env`：与 `janus_project.yml` 位于同一目录
4. `~/.janus/.env`：用户全局的回退文件

规则：

- 变量名必须为**大写**（`[A-Z_][A-Z0-9_]*`）
- 小写的 `${foo}` 会被当作普通字符串
- `$$` 用于转义字面量美元符号（`a$$b` 变为 `a$b`）
- 缺失的变量会尽早失败，并给出清晰的错误，而不会出现难以理解的驱动认证错误

## Skill 安装路径

`npx skills add` 和 `install.sh` 会根据 `--agent` 参数，把 Skill 写入以下目录之一：

| 模式 | 使用方 | 示例 |
|---|---|---|
| `<project>/.agents/skills/` | 多智能体共享目录 | Amp、Cursor、Cline、OpenCode（项目级）、Codex（项目级） |
| `<project>/.<agent>/skills/` | 智能体专用目录 | Claude Code（`.claude/skills/`）、Continue（`.continue/skills/`）、Windsurf（`.windsurf/skills/`） |
| `<project>/skills/` | 仓库根目录约定 | OpenClaw |
| `~/.<agent>/skills/` | 全局安装 | `~/.codex/skills/`、`~/.gemini/skills/`、`~/.deepagents/agent/skills/` |

每个智能体的选择方式参见[安装](/oss/get_started/installation)。

## 推荐的 `.gitignore`

对于 Janus 项目，请添加：

```text
target/
.janus/memory/
.env
```

如果应用仓库通过 SDK 或 CLI 使用 Janus AI，还可以考虑：

```text
.janus/                 # 如果运行时状态目录创建在仓库根目录下
```

## 权限

| 文件 | 权限 |
|---|---|
| `~/.janus/profiles.yml` | `0600`：仅所有者可读写。以原子方式写入（临时文件 + 重命名）。 |
| `<project>/.env` | 建议仅所有者可读写。 |
| `~/.janus/.env` | 建议仅所有者可读写。 |

`profiles.yml` 中的密钥以 `${VAR}` 占位符的形式保存，该文件从不包含明文凭据。`janus profile debug` 会对名为 `password`、`credentials`、`secret` 或 `token` 的字段进行脱敏。

## 另请参阅

- [CLI 参考](./cli.md)：每个命令和参数
- [MDL Schema 参考](./mdl.md)：项目中的每个 YAML 字段
- [管理项目](/oss/guides/manage_project)：生命周期命令和配置文件工作流

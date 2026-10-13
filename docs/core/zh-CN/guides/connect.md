---
sidebar_label: 连接你的数据库
---

# 连接你的数据库

Janus AI 通过**连接配置文件（profile）**与你的数据库通信。配置文件保存凭据和连接信息，位于 `~/.janus/profiles.yml`。配置文件绑定到项目后，之后的每条 CLI 命令和 SDK 调用都会使用它。

无论使用哪种数据库，流程都相同：

1. **安装对应数据源的连接器扩展**。
2. **用 `janus profile add` 创建配置文件**（或让 `onboarding` 指南替你完成）。
3. **用 `janus context set-profile` 把配置文件绑定到项目**。
4. **用 `generate-mdl` 指南生成 MDL**（或手动编写）。
5. **开始查询。**

如果你安装了 AI 编码智能体，`/janus` Skill 会驱动整个流程，参见[安装](/oss/get_started/installation)。

## 支持的数据源

| 数据源 | 连接器扩展 |
|---|---|
| DuckDB | _（已内置）_ |
| PostgreSQL | `postgres` |
| MySQL | `mysql` |
| BigQuery | `bigquery` |
| Snowflake | `snowflake` |
| ClickHouse | `clickhouse` |
| Trino / Presto | `trino` |
| SQL Server | `mssql` |
| Databricks | `databricks` |
| Redshift | `redshift` |
| Oracle | `oracle` |
| Athena | `athena` |
| Spark | `spark` |

可以一次安装一个或多个扩展：

```bash
pip install "janusai[postgres,bigquery,main]"
```

## 查看连接字段

要查看某个连接器需要和接受的确切字段，运行：

```bash
janus docs connection-info <ds>
```

输出直接从引擎的连接 Schema 生成，因此始终与你安装的 `janusai` 版本一致。示例：

```bash
janus docs connection-info postgres
janus docs connection-info bigquery
janus docs connection-info snowflake
```

不要死记字段名，以 CLI 为准。

## 创建配置文件

最简单的方式是浏览器界面：

```bash
janus profile add my-db --ui
```

或使用交互式流程：

```bash
janus profile add my-db --interactive
```

也可以从 YAML 文件导入（推荐在智能体驱动的场景中使用，这样密钥可以保存在 `.env` 中）：

```bash
janus profile add my-db --from-file connection.yml
```

## 验证连接

```bash
janus profile debug   # 显示解析后的配置（密钥已脱敏）
janus --sql "SELECT 1"
```

如果连接失败，请检查凭据、网络连通性、SSL 设置，以及云数据库侧的 IP 白名单。

## 把配置文件绑定到项目

```bash
cd ~/my-project
janus context set-profile my-db
```

这会在 `janus_project.yml` 中写入 `profile: my-db` 和 `data_source: <ds>`。之后该项目中的命令都会使用这个配置文件，而不受全局激活的配置文件影响。

## 下一步

- [为你的业务建模](/oss/guides/model)：让智能体根据你的 Schema 搭建 MDL
- [提升回答质量](/oss/guides/refine)：通过记忆和指令闭合反馈回路
- [管理项目](/oss/guides/manage_project)：多环境的配置文件工作流

---
sidebar_label: 管理项目
---

# 管理项目

Janus 项目是 MDL 编写、版本控制和部署的基本单元。本指南涵盖其完整生命周期：初始化、校验、构建、连接配置（profile）管理、多环境工作流以及迁移。

## 完成后你会得到

- 清楚理解哪些文件位于项目中，哪些全局位于 `~/.janus/` 中
- 将生命周期命令接入你的编辑器或 CI
- 为同一项目配置好 dev / staging / prod 等多个 profile
- 一种无需接触密钥即可安全切换环境的方法

## 项目生命周期

```bash
janus context init              # scaffold a new project in cwd
janus context validate          # check YAML structure (no DB required)
janus context build             # compile YAML to target/mdl.json
janus context upgrade           # upgrade to the latest schema_version
janus context set-profile pg    # bind a connection profile to the project
janus memory index              # index schema + knowledge/ for recall
```

首次设置的典型流程：

```bash
mkdir my_project && cd my_project
janus context init
# (edit models/, relationships.yml, knowledge/ — usually agent-driven)
janus context validate
janus context build
janus profile add pg-dev --from-file dev.yml --activate
janus context set-profile pg-dev
janus memory index
janus --sql "SELECT 1"
```

编辑模型后，请重新构建并重建索引：

```bash
janus context build
janus memory index
```

## 项目根目录下的 `janus_project.yml`

```yaml
schema_version: 5
name: my_project
version: "1.0"
catalog: janus
schema: public
data_source: postgres
profile: pg-dev
```

| 字段 | 用途 |
|---|---|
| `schema_version` | 项目布局版本（当前为 **5**，即下方的布局）。由 CLI 管理，使用 `janus context upgrade` 升级。`knowledge/` 知识库在 `knowledge/knowledge.yml` 中维护自己的版本，与此版本相互独立。 |
| `name` | 项目标识符。 |
| `version` | 你自己的项目版本（自由格式）。 |
| `catalog` / `schema` | **Janus AI 命名空间**，而非你的数据库 catalog 或 schema。默认值：`janus` / `public`。 |
| `data_source` | 数据源类型，例如 `postgres`、`bigquery` 等。由 `janus context set-profile` 设置。 |
| `profile` | 绑定的连接 profile。由 `janus context set-profile` 设置。 |

> 同样的字段名 `catalog` 和 `schema` 也出现在每个模型的 `table_reference` 中，用于指向数据库。请勿混淆两者，完整区别参见 [MDL Schema 参考](/oss/reference/mdl)。

## 项目布局

`janus context init` 会生成当前布局（**v5**）：每个模型和每个视图各自一个文件夹，`cubes/` 用于存放预聚合的语义对象，一等公民的 `knowledge/` 知识库，以及（后期添加的）CReport `apps/`。

下列内容都位于**项目中**（受版本控制），但 `target/`（构建输出）和 `.janus/`（项目本地运行时状态）可以加入 gitignore。连接凭据和全局 CLI 状态单独存放在 `~/.janus/` 下（参见[Profile 存放位置](#where-profiles-live)）。

```text
my_project/
├── janus_project.yml          # project manifest (fields above)
│
├── models/<name>/            # MDL — one folder per model
│   ├── metadata.yml          #   columns, primary_key, table_reference, …
│   └── ref_sql.sql           #   (optional) SQL-defined model body
├── views/<name>/             # MDL — one folder per view
│   ├── metadata.yml          #   view definition
│   └── sql.yml               #   (optional) statement in a separate file
├── relationships.yml         # MDL — all relationships between models
├── cubes/<name>/             # (optional) pre-aggregation cubes
│   └── metadata.yml          #   base_object, measures, dimensions, …
│
├── knowledge/                # knowledge base (committed)
│   ├── rules/                #   business rules — read by `janus context instructions`
│   ├── glossary/             #   business-term definitions
│   ├── metrics/              #   named metric definitions
│   ├── caveats/              #   data caveats / gotchas
│   ├── sql/                  #   NL→SQL pairs — source of truth for memory
│   └── knowledge.yml         #   knowledge-axis schema_version (decoupled from MDL)
│
├── AGENTS.md                 # AI agent workflow guidance for this project
│
├── apps/<name>/              # (optional) generated CReport apps — see the CReport guide
│   ├── index.html            #   app entry point
│   └── mdl.json              #   compiled MDL copied into the app
│
├── target/
│   └── mdl.json              # compiled MDL — `janus context build`
└── .janus/                    # project-local runtime state (gitignore-able)
    ├── memory/               #   LanceDB semantic index over knowledge/sql/ — `janus memory index`
    └── apps.yml              #   CReport app index — written by `janus creport register`
```

`knowledge/` 承载数据库 Schema 无法表达的内容：业务规则、术语表条目、命名指标、数据注意事项，以及由 `janus memory store` 写入的 `knowledge/sql/` 自然语言到 SQL 配对。它在 `knowledge.yml` 中拥有**自己的** `schema_version`，与 MDL 布局版本解耦，因为知识与数据模型的演进节奏不同。`knowledge/rules/` 取代了较早的单文件 `instructions.md`，`knowledge/sql/` 取代了 `queries.yml`。这两个旧文件为了向后兼容仍会被读取，但不再生成。

`memory` 额外依赖会在 `.janus/memory/` 下构建语义（embedding）索引；未安装时，召回会直接读取 `knowledge/sql/*.md`。因此，真正的事实来源是 `knowledge/sql/`，而不是索引。

`apps/<name>/` 和 `.janus/apps.yml` 由 [CReport 工作流](creport.md)添加；`.janus/apps.yml` 由 `janus creport register/remove` 机器写入，切勿手动编辑。

## Profile 管理

Profile 将连接凭据与项目定义分离。同一个 MDL 项目可以通过切换 profile 连接到多个数据库。

```bash
janus profile list                  # list all profiles (* marks active)
janus profile add pg-prod --ui      # create via browser form
janus profile switch pg-prod        # change the globally active profile
janus profile debug                 # show resolved config (secrets masked)
janus profile rm old-db             # remove a profile
```

### Profile 存放位置 {#where-profiles-live}

```text
~/.janus/profiles.yml      # global, all profiles + active pointer
~/.janus/config.yml        # global CLI preferences, default_project
```

该文件以 `0600` 权限写入。密钥使用 `${ENV_VAR}` 插值，参见下方的[密钥与 `.env` 文件](#secrets-and-env-files)。

### Profile 与项目速览

| | Profile | 项目 |
|---|---|---|
| **内容** | 连接凭据 | MDL 模型定义 |
| **位置** | `~/.janus/profiles.yml`（全局） | `<project>/janus_project.yml` + `models/` |
| **范围** | 在所有项目间共享 | 每个项目独立，受版本控制 |
| **密钥** | 包含密钥 | 无，可安全提交 |

## 多环境工作流

同一个 MDL 项目可以为不同环境绑定不同的 profile。

### 模式一：全局切换 profile

```bash
janus profile switch pg-dev      # work against dev
janus profile switch pg-prod     # switch to prod for one query
janus profile switch pg-dev      # back to dev
```

### 模式二：为项目绑定 profile

```bash
cd ~/projects/sales
janus context set-profile pg-prod   # writes profile + data_source into janus_project.yml
```

绑定之后，该项目中的每条命令都会使用 `pg-prod`，无论全局激活的是哪个 profile。当你同时打开多个项目时，这一点非常有用。

### 模式三：按 shell 覆盖

```bash
export JANUS_PROJECT_HOME=~/projects/sales
janus --connection-file ./connection.yml --sql "SELECT 1"
```

适用于需要指向特定数据库、又不希望修改 `~/.janus/profiles.yml` 的 CI 任务。

## 密钥与 `.env` 文件 {#secrets-and-env-files}

任何 profile 值都可以引用 `${VAR_NAME}` 占位符。解析顺序（首个匹配者胜出）：

1. `os.environ`：在你的 shell 中导出的变量
2. `$CWD/.env`：你运行 `janus` 时所在的目录
3. `<project>/.env`：与 `janus_project.yml` 位于同一位置
4. `~/.janus/.env`：用户全局的备选项

```yaml
# ~/.janus/profiles.yml
profiles:
  pg-prod:
    datasource: postgres
    host: db.example.com
    port: '5432'
    database: janus
    user: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
```

```bash
# .env (in project root, gitignored)
POSTGRES_USER=paul
POSTGRES_PASSWORD=s3cr3t
```

规则：

- 变量名必须为**大写**（`[A-Z_][A-Z0-9_]*`）
- `$$` 用于转义字面量美元符号
- 缺失的变量会尽早失败，并给出清晰的错误信息，而不是晦涩的驱动错误

AI 编码智能体**绝不**应在聊天中索要凭据。智能体会编写一个引用 `${POSTGRES_PASSWORD}` 的 profile，并指示你通过编辑器在 `.env` 中填入该值。

## 从已有清单迁移

`janus context init` 接受两个导入标志，每个对应一种外部清单格式。两者都会生成相同的 janus 项目布局，可直接用于 `validate` 和 `build`。二者互斥。

| 来源 | 命令 | 使用场景 |
|---|---|---|
| Janus `mdl.json`（camelCase） | `janus context init --from-mdl /path/to/mdl.json --path my_project` | 你有一个来自早期 Janus 配置的旧版 `mdl.json`。 |
| OSI `semantic_model.yaml` | `janus context init --from-osi /path/to/semantic_model.yaml --data-source postgres --path my_project` | 你有一个[开放语义互换（OSI）](./osi.md)文件，并希望脱离 OSI 流程，使用仅 Janus 支持的功能（Cube、视图、RLAC）。 |

导入之后：

```bash
janus context validate --path my_project
janus context build --path my_project
```

如果目标目录已有项目文件，请使用 `--force` 覆盖。

对于 `--from-osi`，请参阅专门的 [OSI 指南](./osi.md)。它还介绍了另一种做法：保留 OSI 作为事实来源（`janus context build --from-osi`），而不是一次性迁移。

## 升级已有项目

当新的布局 `schema_version` 发布时，使用以下命令升级：

```bash
janus context upgrade            # bumps to the latest schema_version
janus context upgrade --to 5     # bump to a specific version
janus context upgrade --dry-run  # preview without writing
```

升级后，请重新校验并重新构建：

```bash
janus context validate
janus context build
```

某些版本除了自动重写版本号之外还会增加内容。例如 **v5** 引入了 `knowledge/`，并使其成为业务规则和自然语言到 SQL 记忆的归属位置，因此需要额外的步骤，将 `instructions.md` 和已有的 LanceDB 索引迁移过来。各版本的具体步骤参见[迁移参考](/oss/reference/migration)。

## 何时需要回到这里

- 添加新环境（staging / preview / 客户 X）
- 为新团队成员办理入职（指引他们完成 `~/.janus/profiles.yml` 的设置）
- 某次发布中出现 schema_version 升级
- 从其他工具的语义层清单迁移

## 另请参阅

- [MDL Schema 参考](/oss/reference/mdl)：项目 YAML 文件中的每个字段
- [运维参考](/oss/reference/operational)：路径、环境变量和发现规则
- [连接你的数据](./connect.md)：初始连接步骤

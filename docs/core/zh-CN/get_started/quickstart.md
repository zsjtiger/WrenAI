---
sidebar_label: 快速开始（jaffle_shop）
---

import ArchStrip from '@site/src/components/ArchStrip';

# 快速开始：使用 jaffle_shop 的 Janus CLI

使用 **Janus AI CLI** 和 **Claude Code**，用自然语言向 **jaffle_shop** 数据集提问。无需云数据库、无需 Docker，也无需任何额外基础设施。

> **耗时：** 约 15 分钟
>
> **你将获得：** 一个本地上下文层加记忆系统，让 AI 智能体通过理解数据的含义（而不仅仅是 Schema），编写出准确的 SQL。

<ArchStrip variant="cli" />

## 本指南用到的术语

本指南会在前几步引入三个概念。开始前请先浏览一遍：

- **Janus CLI（`janus`）**：运行这一切的 Python CLI。它连接数据库、保存建模文件、通过上下文层执行 SQL，并管理本地记忆索引。（[CLI 参考 →](/oss/reference/cli)）
- **MDL（Modeling Definition Language，建模定义语言）**：位于 `models/`、`views/` 和 `relationships.yml` 下的 YAML 文件，用业务语言描述你的表、列和关联。智能体读取 MDL，而不是从原始 Schema 中猜测。（[MDL 概念 →](/oss/concepts/what_is_mdl) · [Janus 项目指南 →](/oss/reference/mdl)）
- **jaffle_shop**：dbt Labs 提供的公开示例数据库。我们使用它，这样你无需自备数据库即可跟随本快速开始。它是一家虚构的电商业务，原始数据包括客户、订单和支付；`dbt build` 会把它转换为两张分析表 `customers` 和 `orders`。*（想跳过 jaffle_shop、改用自己的数据库？完成第 2 步的安装后，直接跳到[连接你的数据库](/oss/guides/connect)。）*
- **技能（Skills）**：Markdown 格式的工作流指南，告诉 AI 编码智能体（Claude Code、Openclaw、Hermes、Codex 等）如何操作 CLI。你只需安装一个 `janus` 发现桩（stub），它会按需从 CLI 获取指南。本快速开始使用两份指南：`generate-mdl`（一次性搭建脚手架）和 `usage`（日常查询）。（[技能概念 →](/oss/reference/skills)）

---

## 前提条件

- **Claude Code**：已安装并完成认证（[安装指南](https://docs.anthropic.com/en/docs/claude-code/overview)）
- **Python 3.11+**
- **Node.js / npm**：如果使用 `npx` 安装技能则需要（见第 3 步）
- **Git**

---

## 第 0 步：创建 Python 虚拟环境

安装任何包之前，先创建并激活一个虚拟环境。这可以让 dbt 和 janusai 的依赖与系统 Python 隔离：

```bash
python3 -m venv ~/.venvs/janus
source ~/.venvs/janus/bin/activate
```

> **提示：** 在每个新的终端会话中，运行 `dbt` 或 `janus` 命令之前，先激活此环境（`source ~/.venvs/janus/bin/activate`）。

---

## 第 1 步：导入 jaffle_shop 数据集

克隆 dbt 的 jaffle\_shop 项目并构建 DuckDB 数据库：

```bash
git clone https://github.com/dbt-labs/jaffle_shop_duckdb.git
cd jaffle_shop_duckdb
pip install dbt-core dbt-duckdb
dbt build
```

验证数据库文件已创建：

```bash
ls jaffle_shop.duckdb
```

`dbt build` 会导入三张原始表，然后在其之上构建三个 staging 视图和两张分析表：

| 对象 | 名称 |
|---------|-------|
| 分析表 —— **在这里建模** | `customers`、`orders` |
| Staging 视图 | `stg_customers`、`stg_orders`、`stg_payments` |
| 原始种子表 | `raw_customers`、`raw_orders`、`raw_payments` |

本快速开始只需要 `customers` 和 `orders`。`raw_*` 和 `stg_*` 对象是 dbt 的中间层——请不要把它们放进你的 Janus 项目，这样智能体对每个概念只会看到一张明确的表。

记下此目录的**绝对路径**，配置 profile 时需要用到它：

```bash
pwd
# e.g. /Users/you/jaffle_shop_duckdb
```

---

## 第 2 步：安装 janusai Python 包

本快速开始请安装 **DuckDB + memory + UI + 交互式提示** 版本：

```bash
pip install "janusai[memory,main]"
```

DuckDB 默认已包含，因此无需额外的 extra。若要使用其他数据源，请追加对应的连接器 extra（例如 `pip install "janusai[memory,main,postgres]"`）。

> **可用的 extras：**
> - `postgres`、`mysql`、`bigquery`、`snowflake`、`clickhouse`、`trino`、`mssql`、`databricks`、`redshift`、`athena`、`oracle`、`spark`：数据源连接器
> - `memory`：基于 LanceDB 的语义记忆（NL-SQL 召回、嵌入检索）。**可选**，但推荐用于本快速开始。
> - `main`：交互式提示 + 基于浏览器的 profile UI

验证安装：

```bash
janus version
```

---

## 第 3 步：安装 CLI 技能

技能是告诉 AI 编码智能体如何高效使用 Janus CLI 的工作流指南。安装发现桩，它会按需从 CLI 获取指南：

```bash
npx skills add CrossNow/JanusAI
# or:
curl -fsSL https://raw.githubusercontent.com/CrossNow/JanusAI/main/skills/install.sh | bash
```

CLI 会自动检测你已安装的智能体。若要指定某个智能体，请添加 `--agent <name>`（例如 `claude-code`、`cursor`、`windsurf`、`cline`）。只会安装一个技能（`janus`）；下方的工作流指南通过 `janus skills get <name>` 按需提供。

本快速开始使用其中两份指南：

| 指南 | 用途 |
|-------|---------|
| **usage** | 日常工作流：收集上下文、召回历史查询、编写 SQL、保存结果 |
| **generate-mdl** | 一次性设置：探索数据库 Schema 并生成 MDL 项目 |

完整的指南列表（包括 `onboarding` 和 `dlt-connector`），请参见[技能参考](/oss/reference/skills)。

---

## 第 4 步：设置 profile

profile 保存数据库连接信息（类似 dbt profiles）。为 jaffle\_shop 的 DuckDB 数据库创建一个：

### 选项 A：浏览器 UI（推荐）

```bash
janus profile add jaffle-shop --ui
```

这会打开一个浏览器表单。请填写：

- **数据源：** `duckdb`
- **数据库路径：** `/Users/you/jaffle_shop_duckdb`，即包含 `.duckdb` 文件的**目录**，而不是 `.duckdb` 文件本身（使用第 1 步中你的绝对路径）

### 选项 B：交互式 CLI

```bash
janus profile add jaffle-shop --interactive
```

按提示输入 profile 名称、数据源和连接字段。

### 选项 C：从文件导入

创建一个 YAML 文件 `jaffle-profile.yml`：

```yaml
datasource: duckdb
url: /Users/you/jaffle_shop_duckdb
format: duckdb
```

然后导入它：

```bash
janus profile add jaffle-shop --from-file jaffle-profile.yml
```

---

验证 profile 已激活：

```bash
janus profile list
```

你应该会看到 `jaffle-shop` 被标记为 active。测试连接：

```bash
janus profile debug
```

---

## 第 5 步：初始化 Janus 项目

为项目创建一个新目录并搭建项目结构：

```bash
mkdir -p ~/jaffle-janus && cd ~/jaffle-janus
janus context init
```

这会创建：

```
~/jaffle-janus/
├── janus_project.yml        # project metadata
├── models/                 # one folder per table
├── views/                  # reusable SQL views
├── cubes/                  # pre-aggregation metrics
├── relationships.yml       # table join definitions
└── knowledge/              # business rules + NL→SQL pairs for the AI
```

生成的 `janus_project.yml` 包含 `catalog` 和 `schema` 的默认值：

> **注意：** `janus_project.yml` 中的 `catalog` 和 `schema` 定义的是 **Janus AI 命名空间**。它们与你数据库的 catalog 或 schema 无关。保留默认值（`janus` / `public`）即可。每张表在数据库中的实际位置，在 `models` 的 `table_reference` 部分按模型单独指定。

将刚创建的 profile 绑定到此项目：

```bash
janus context set-profile jaffle-shop
```

这会把 `profile: jaffle-shop` 和 `data_source: duckdb` 写入 `janus_project.yml`，将此项目锁定到其连接。之后的命令（以及 SDK）都会使用绑定的 profile，而不论全局激活的是哪个 profile，因此在其他地方执行 `janus profile switch` 不会意外改变本项目的查询目标。

---

## 第 6 步：使用 Claude Code 生成 MDL

首先，删除 `janus context init` 创建的示例模型和视图。它们只是占位符，将被生成的模型取代：

```bash
rm -rf models/example_model views/example_view
```

现在让 Claude Code 探索数据库并生成 MDL 项目文件。在**项目目录中**打开 Claude Code：

```bash
cd ~/jaffle-janus
claude
```

然后提问：

```
Use the /janus skill to explore the jaffle_shop database and generate the MDL
for the customers and orders tables. Skip the raw_* seeds and stg_* views.
The data source is DuckDB.
```

`janus` 技能会将其识别为脚手架任务，并调用 `generate-mdl` 指南（`janus skills get generate-mdl`）来驱动该任务。

Claude Code 将会：

1. **发现表**：`customers` 和 `orders`
2. **使用 SQLAlchemy 或 `information_schema` 检查列和类型**
3. **通过 `janus utils parse-type` 规范化类型**
4. **编写模型 YAML 文件**，每张表在 `models/` 下一个文件夹
5. **从外键和命名约定推断关系**
6. **添加描述**：Claude 可能会请你描述关键的表和列
7. **校验并构建**：`janus context validate` → `janus context build`
8. **为记忆建立索引**：`janus memory index`（生成种子 NL-SQL 示例）

> **提示：** 如果在 macOS 上执行上面的索引步骤 `janus memory index` 时卡顿数十秒，这并非故障。首次运行 `janus memory` 命令时会加载大型未签名原生库（lancedb 和 torch，约 800MB），macOS 会在它们首次执行时进行一次性的 XProtect 安全扫描。这是 macOS 的预期行为，并非 Janus 的问题，而且只发生一次：之后每个 `janus memory` 命令都会以正常速度运行。为避免现场演示时出现停顿，请在安装后立即运行一次任意 `janus memory` 命令，并等待其完成。

完成后，验证项目：

```bash
janus context show
janus memory status
```

---

## 第 7 步：开始提问

一切就绪。在 Claude Code 中，直接用自然语言提问：

```
How many customers placed more than one order?
```

```
Which 5 customers have the highest lifetime value?
```

```
Show me the monthly order count trend.
```

在幕后，Claude Code 会使用 **usage** 指南来：

1. **获取上下文**（`janus memory fetch`）：为你的问题查找相关的表和列
2. **召回示例**（`janus memory recall`）：查找相似的历史查询
3. **使用上下文层编写 SQL**（模型名称，而非原始表名）
4. **执行**（`janus --sql "..."`）：通过 Janus 引擎运行
5. **保存**（`janus memory store`）：将成功的 NL-SQL 对保存，供未来召回

提问越多，系统就越智能。每一条被保存的查询都会提高未来的召回准确率。

---

## 第 8 步：添加并查询 Cube（可选）

**Cube** 是一种语义聚合对象：一个模型加上声明好的度量、维度和时间粒度。`generate-mdl` 会生成表和关系的脚手架，但不会生成 Cube，因此现在请借助 Claude Code 添加一个。

### 第 8a 步：添加 Cube

在 Claude Code 中：

```
Use the /janus skill to add a cube named "revenue" over the orders model:
total revenue as SUM(amount), an order count, broken down by status and
monthly by order_date.
```

Claude Code 会起草 Cube 的 YAML，与你确认后将其写入 `cubes/revenue/metadata.yml`，并重新构建 manifest。

> **想手动编写？** 请参阅 [Cube 指南](../guides/cubes.md)了解完整的 YAML 结构，然后运行 `janus context build`。

### 第 8b 步：查询 Cube

```bash
janus cube list

janus cube query \
  --cube revenue \
  --measures total,order_count \
  --time-dimension "order_date:month"
```

`--time-dimension` 接受 `<name>:<granularity>` 格式。可以添加 `--dimensions status` 或 `--filter "status:eq:completed"` 进行进一步切片。所有选项请参见 [Cube 指南](../guides/cubes.md)和 [CLI 参考](../reference/cli.md#janus-cube--pre-aggregation-queries)。

---

## 第 9 步：构建并部署 CReport 仪表盘（可选）

你已经得到了答案。现在把它变成可分享的报告。CReport 会根据项目的上下文构建一个浏览器端仪表盘，并将其部署到你自己的 Vercel 或 Cloudflare Pages 账户。整个过程都通过智能体驱动。

在 Claude Code 中：

```
Use the /janus skill to build a CReport dashboard from the revenue cube:
monthly revenue and order count, filterable by status. Then preview it locally.
```

`janus` 技能会调用 `creport` 指南（`janus skills get creport`）来驱动构建：

1. **构建指令**（`janus creport build`）：将 MDL 和固定版本的 `janus-core-wasm` 注入应用规格。
2. **编写应用**：在 `apps/<name>/` 下编写一个自包含的应用，选择能回答问题的图表。
3. **生成数据快照**：导出仪表盘所需的数据（默认快照模式），使应用完全在客户端运行，无需后端。
4. **验证并预览**（`janus creport verify`，然后 `janus creport open`）：运行预检并在本地提供应用服务。

打开智能体打印的预览 URL（例如 `http://127.0.0.1:8848/`），点击浏览。用自然语言提出修改（例如"改成柱状图"、"去掉状态筛选器"），智能体会重新构建。

当效果满意后，请智能体进行部署：

```
Deploy the dashboard to Vercel.
```

你需要提供部署令牌：将 `VERCEL_TOKEN`（或 `CLOUDFLARE_API_TOKEN` 加上 `CLOUDFLARE_ACCOUNT_ID`）添加到 `~/.janus/.env`，然后告诉智能体继续。它会运行 `janus creport deploy` 并返回一个可分享的 URL。部署默认发布到预览 URL；如需正式发布，请说"发布到生产环境"（ship it to production）。

> **注意：** 新建的 Vercel 项目默认会对未登录的访问者返回 HTTP 401。部署本身已成功；要让 URL 公开，请在 Project → Settings → Deployment Protection → Vercel Authentication → Disabled 中一次性关闭 Vercel Authentication。

完整流程请参见[构建并部署 CReport 应用](../guides/creport.md)。

---

## 项目中有什么

设置完成后，项目目录如下所示：

```
~/jaffle-janus/
├── janus_project.yml
├── models/
│   ├── customers/
│   │   └── metadata.yml        # table schema and descriptions
│   └── orders/
│       └── metadata.yml
├── views/
├── cubes/                      # only if you did Step 8
│   └── revenue/
│       └── metadata.yml        # measures + dimensions for aggregation
├── relationships.yml           # e.g. orders → customers (many_to_one)
├── knowledge/
│   ├── rules/                  # your business rules
│   └── sql/                    # confirmed NL→SQL pairs (janus memory store)
├── .janus/
│   └── memory/                 # LanceDB index (auto-managed)
└── target/
    └── mdl.json                # compiled manifest
```

需要重点定制的文件：

- **`knowledge/rules/`**：添加业务规则、命名约定或查询指南。每个主题一个 markdown 文件，并用 `##` 标题组织。示例（`knowledge/rules/conventions.md`）：

  ```markdown
  ## Naming Conventions
  - "revenue" always means the order `amount`, not one of the per-payment-method
    columns like `credit_card_amount`
  - "active customers" means customers with at least one order in the last 90 days

  ## Query Rules
  - Always use order_date for time-based filtering, not created_at
  ```

- **`models/*/metadata.yml`**：为模型和列添加或完善 `properties.description`。描述越好，记忆搜索效果越好。

- **`relationships.yml`**：添加或修正连接条件。错误的关系会导致静默的查询错误。

修改任何文件后，请重新构建并重新索引：

```bash
janus context validate
janus context build
janus memory index
```

---

## 常用命令参考

| 任务 | 命令 |
|------|---------|
| 执行 SQL | `janus --sql "SELECT ..." -o table` |
| 预览计划中的 SQL | `janus dry-plan --sql "SELECT ..."` |
| 校验 SQL | `janus dry-run --sql "SELECT ..."` |
| 显示项目上下文 | `janus context show` |
| 显示指令 | `janus context instructions` |
| 构建 manifest | `janus context build` |
| 为某个问题获取上下文 | `janus memory fetch --query "..."` |
| 召回相似查询 | `janus memory recall --query "..."` |
| 保存一条 NL-SQL 对 | `janus memory store --nl "..." --sql "..."` |
| 检查记忆状态 | `janus memory status` |
| 重新索引记忆 | `janus memory index` |
| 切换 profile | `janus profile switch <name>` |
| 列出 profile | `janus profile list` |

---

## 后续步骤

- **添加视图**：为常见问题添加视图。带有良好描述的视图会成为高质量的召回示例
- **持续完善指令**：每当发现 AI 经常出错的查询模式，就补充相应说明

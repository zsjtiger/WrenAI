# Skills

Janus AI 提供 **Skills**：可复用的 AI 智能体工作流指南，用于指导 Claude Code（或其他 AI 编码智能体）如何通过 Janus CLI 完成多步骤任务。每个 Skill 都是一份结构化的 Markdown 指南，包含决策树、智能体侧的规则，以及指向更深入文档的引用。

## 新的交付模式

早期版本的 Janus 把每个 Skill 作为一个独立的 Markdown 文件夹，安装到智能体的 Skill 目录中（`~/.claude/skills/`、Cursor 的 `rules/` 等）。这种模式有两个反复出现的问题：打包的 Markdown 会与已安装的 CLI 版本产生偏差，并且智能体会预先加载全部内容，无论是否需要。

从 Janus `0.8` 开始，Skill 内容**存放在 `janus` CLI 内部**，按需提供：

- 智能体中只会安装一个约 50 行的**发现存根**（`skills/janus/SKILL.md`）。它告诉智能体，工作流指南和提示词模板需要从 CLI 获取。
- 实际的工作流指南存放在 `janusai` Python 包中，由 `janus skills get <name>` 输出到标准输出。
- 提示词模板的提供方式相同：`janus ask "<q>" --guided|--direct`。
  参考文档在网上的 [`docs/core/`](https://github.com/CrossNow/JanusAI/tree/main/docs/core) 下。

由于内容随 wheel 包一起分发，智能体读取的版本始终与已安装的 CLI 一致。

## 可用的 Skill

| Skill | 获取命令 | 用途 |
|-------|-----------|---------|
| **onboarding** | `janus skills get onboarding` | 入口：环境检查、项目脚手架、配置文件设置、第一条查询 |
| **usage** | `janus skills get usage` | 日常工作流：收集 Schema 上下文、召回历史查询、编写 SQL、执行、保存结果 |
| **generate-mdl** | `janus skills get generate-mdl` | 一次性设置：探索数据库 Schema、规范化类型、搭建 MDL YAML 项目 |
| **enrich-context** | `janus skills get enrich-context` | 补充 Schema 无法表达的业务上下文：枚举、单位、空值语义、默认过滤条件、同义词、货币规则，以及以 Cube 形式定义的命名聚合指标，可通过追问（grill）或自动驾驶模式完成 |
| **dlt-connector** | `janus skills get dlt-connector` | 通过 dlt 把 SaaS API（HubSpot、Stripe、Salesforce、GitHub、Slack 等）接入 DuckDB，然后自动生成 Janus 项目 |
| **creport** | `janus skills get creport` | 把项目的上下文层转换为可分享的浏览器端 CReport Web 应用，并部署到 Vercel 或 Cloudflare Pages |

使用 `janus skills list` 列出所有 Skill。

## 安装

```bash
pip install janusai                       # 核心 CLI（已内置 DuckDB）
npx skills add CrossNow/JanusAI             # 为你的智能体安装一行式发现存根
```

安装程序会自动检测 Claude Code、Cursor、Cline、Codex 等类似客户端。安装完成后，请开启一个新的智能体会话。存根会在会话开始时加载，之后会按需获取工作流指南。

## 内容如何交付

智能体使用 `janus skills get <name>` 获取指南。第一次调用会返回 SKILL.md 的正文，即一份聚焦的工作流指南。当智能体需要更深入的内容时，可以请求：

```bash
janus skills get <name> --full             # 把该 Skill 的 references/ 内联输出
janus skills get <name> --script <stem>    # 输出内置脚本的源代码
```

提示词模板的获取方式相同：

```bash
janus ask "<question>" --guided            # 面向能力较弱的 LLM
janus ask "<question>" --direct            # 面向能力较强的 LLM
```

参考文档在网上的 [`docs/core/`](https://github.com/CrossNow/JanusAI/tree/main/docs/core) 下。

一个内置的 CI 守卫（`tests/unit/test_served_content_guard.py`）会扫描已提供的 Skill 内容、参考文档和 ask 模板中每一条 `janus <cmd>` 调用，并与真实的 CLI 命令树进行比对。因此，指南不可能告诉智能体运行一个不存在的命令或参数。

---

## onboarding

入口 Skill。它会引导智能体完成完整的设置流程：环境检查、项目脚手架、连接配置、MDL 生成和第一条查询，并在每一步路由到相应的文档和其他 Skill。Skill 本身只关注智能体侧的规则（每轮只做一步，绝不在聊天中索要凭据）。

### 工作流

```text
用户说"安装 janus" / "设置 janus"
  │
  ├── 预检（只读）
  │     Python 3.11+、虚拟环境、janus CLI、工作目录
  │
  ├── 分支：使用内置示例还是自己的数据库？
  │     示例 → 快速开始指南，结束
  │     自己的数据库 → 继续
  │
  ├── 第 1 步：项目名称 + 数据库类型
  │     （一起询问，此时还不需要凭据）
  │
  ├── 第 2 步：项目设置（批量）
  │     mkdir、pip install、janus context init，
  │     通过连接器内省生成 .env 模板
  │
  ├── 第 3 步：用户在编辑器中填写 .env
  │     （智能体永远看不到凭据的值）
  │
  ├── 第 4 步：验证连接
  │     janus profile debug
  │
  ├── 第 5 步：生成 MDL
  │     janus skills get generate-mdl
  │
  └── 第 6 步：第一条查询
        janus --sql "SELECT 1"（健全性检查）
        然后对生成的 MDL 执行真实查询
```

### 强制执行的智能体侧规则

| 规则 | 原因 |
|------|-----|
| **每次往返只做一步** | 避免让用户不知所措，保持每轮对话聚焦 |
| **绝不在聊天中索要凭据** | 主机、端口、用户名、密码和令牌都只能通过 `.env` 提供 |
| **绝不编造连接字段名** | 始终运行 `janus docs connection-info <ds>` 获取真实字段 |
| **在 MDL 构建完成之前绝不查询数据库** | 强制智能体先搭建上下文层 |

### 触发时机

发现存根在以下类似表述出现时，会把智能体路由到这里：

- "install janus"
- "set up janus engine"
- "connect a new database"
- "I want to start a Janus project"

### 参考文档（Skill 只指向它们，不重复内容）

- [`docs/core/get_started/installation.md`](https://github.com/CrossNow/JanusAI/blob/main/docs/core/get_started/installation.md)
- [`docs/core/guides/connect.md`](https://github.com/CrossNow/JanusAI/blob/main/docs/core/guides/connect.md)
- [`docs/core/get_started/quickstart.md`](https://github.com/CrossNow/JanusAI/blob/main/docs/core/get_started/quickstart.md)

---

## usage

日常查询的主要 Skill。它会引导智能体完成一次完整的查询生命周期。

### 查询工作流

```text
用户提出问题
  │
  ├── 1. 收集上下文
  │     janus memory fetch -q "..."
  │     janus context instructions      （仅首次查询）
  │
  ├── 2. 召回历史查询
  │     janus memory recall -q "..." --limit 3
  │
  ├── 3. 评估复杂度
  │     简单 → 直接编写 SQL
  │     复杂 → 拆分为子问题
  │
  ├── 4. 编写并执行 SQL
  │     简单：janus --sql "..."
  │     复杂：先 janus dry-plan，再执行
  │
  └── 5. 保存结果
        janus memory store --nl "..." --sql "..."
```

### 错误恢复

该 Skill 包含两层错误诊断策略：

| 层级 | 工具 | 诊断内容 |
|-------|------|-----------|
| **MDL 层** | `janus dry-plan` 失败 | 模型或列名错误、缺少关联关系 |
| **数据库层** | `janus dry-plan` 成功但执行失败 | 类型不匹配、权限、方言问题 |

智能体会先检查 `dry-plan` 的输出，以判断错误出在上下文层还是数据库。

### 其他工作流

| 工作流 | 适用时机 |
|----------|----------|
| **连接新数据源** | `janus profile add` → `janus context init` → 构建 → 建立索引 |
| **MDL 变更之后** | `janus context validate` → `janus context build` → `janus memory index` |

### 参考文件

`janus skills get usage --full` 会内联两份参考文档：

- **memory.md**：何时执行 `index`、`fetch`、`store` 和 `recall` 的决策逻辑。涵盖混合检索策略、默认保存策略以及完整的生命周期示例。
- **janus-sql.md**：基于 CTE 的重写流程是如何工作的。说明引擎如何注入模型 CTE、支持哪些 SQL 特性，以及如何使用 `dry-plan` 逐层诊断错误。

---

## enrich-context

是 `usage` 的"深度补充"搭档。由 Schema 生成的 MDL 只包含数据库能够描述自身的信息，例如列名和类型。业务含义（`status = 'A'` 代表什么、`amount` 是否以分为单位、哪张表是标准表、团队如何定义 ARR）则存在于手册、术语表和分析师的 SQL 中。该 Skill 的作用就是把这些含义纳入项目中可审阅的上下文。

### 两种模式（会话开始时选择）

| 模式 | 行为 | 适用场景 |
|------|----------|----------|
| **追问（Grill）** | 每次只追问一个缺口，提出具体草稿，等待接受、编辑或跳过。在你同意的前提下，可以从实时数据库中抽样低基数列，以发现枚举值和哨兵值。 | 敏感数据，或希望审阅每一处修改 |
| **自动驾驶（Auto-pilot）** | 读取 `raw/` 和当前上下文，直接应用它的最佳推断；只有在原始资料与 MDL 冲突，或新增影响范围较大的内容（新 Cube、视图、关联关系）时，才升级为追问。最后会提供一份带置信度标记的审计报告。 | 从大量文档中批量补充 |

两种模式都只会**新增**内容，绝不修改已有字段。矛盾之处会被列入"请手动修复"清单。

### 它补充的内容

该 Skill 依据一份包含十类缺口的目录工作，覆盖 Schema 无法表达的业务语义：

| 写入位置 | 类别 |
|------|-----------|
| 列的 `properties.description`（文字说明 + `[tag]` 行） | 枚举值含义、单位（美元还是分）、NULL 语义、魔法哨兵值、时间粒度和时区约定 |
| `instructions.md`（固定的 `##` 小节） | 软删除默认过滤条件、业务同义词、跨系统标识符、货币规则、标准表偏好 |
| `cubes/<name>/metadata.yml` | 命名聚合指标（ARR、流失率、DAU），以 Cube 形式提议，这是首选的聚合原语 |
| `queries.yml` / `janus memory store` | 标准的和临时的 NL→SQL 问答对 |

### 触发时机

发现存根在以下类似表述出现时，会把智能体路由到这里：

- "enrich context" / "augment my project" / "grill me on this project"
- "the agent doesn't understand our docs / enum values / units"
- "what does `status = A` mean" / "is this amount in USD or cents"
- "we keep getting wrong aggregations" / "add cubes for ARR / DAU / churn"
- "we have a handbook / glossary / data dictionary the agent should know"

### 参考文件

`janus skills get enrich-context --full` 会内联：

- **gap_catalog.md**：十类缺口，包括触发条件、默认写入位置，以及以文字为主的 `[tag]` 写入格式。
- **cube_proposals.md**：决定提议 Cube、视图还是计算列的决策树，Cube YAML 模板、命名策略、重复检查和验证流程。

---

## generate-mdl

一次性设置 Skill，引导智能体从运行中的数据库创建 MDL 项目。

### 七阶段工作流

| 阶段 | 目标 | 关键操作 |
|-------|------|-------------|
| **1. 连接** | 确认数据库访问 | 通过 SQLAlchemy、驱动或 `janus profile debug` 测试连接 |
| **2. 发现** | 收集 Schema 元数据 | 内省表、列、类型、外键 |
| **3. 规范化** | 转换类型 | `janus utils parse-type` 或 Python 的 `parse_type()` |
| **4. 脚手架** | 编写 YAML 项目 | `janus context init`，创建模型文件和关联关系 |
| **5. 验证** | 检查完整性 | `janus context validate` → `janus context build` |
| **6. 索引** | 初始化记忆 | `janus memory index` |
| **7. 迭代** | 与用户一起优化 | 添加描述、计算列、视图 |

### Schema 发现方法

该 Skill 与工具无关，它会使用智能体可用的任何数据库访问方式：

| 方法 | 最适用于 |
|--------|----------|
| **SQLAlchemy** `inspect()` | 大多数数据库，元数据最丰富（主键、外键、类型） |
| **数据库驱动** | 无法使用 SQLAlchemy 时，直接查询 `information_schema` |
| **通过 janus 执行原始 SQL** | 没有安装 Python 驱动时的引导方式 |

### 类型规范化

原始数据库类型在用于 MDL 之前必须先规范化：

```bash
# 单个类型
janus utils parse-type --type "character varying(255)" --dialect postgres
# → VARCHAR(255)

# 批量（标准输入 JSON）
echo '[{"column":"id","raw_type":"int8"}]' | janus utils parse-types --dialect postgres
```

或者通过 Python：

```python
from janus.type_mapping import parse_type
normalized = parse_type("character varying(255)", "postgres")  # → "VARCHAR(255)"
```

---

## dlt-connector

专门为希望用 SQL 查询 SaaS 数据（HubSpot、Stripe、Salesforce、GitHub、Slack 等）的用户设计的 Skill。它把 [dlt](https://dlthub.com) 抽取管道接入 DuckDB，并在其上自动生成 Janus 项目。

### 四阶段工作流

| 阶段 | 目标 | 关键操作 |
|-------|------|-------------|
| **1. 抽取** | 把 SaaS 数据拉取到本地 DuckDB | `pip install "dlt[duckdb]"`，编写一个小的 `pipeline.py`，设置数据源凭据，运行 `pipeline.run(source)` |
| **2. 建模** | 自动生成 Janus 项目 | 运行内置的 `introspect_dlt` 脚本扫描 DuckDB，通过 `janus.type_mapping.parse_type()` 规范化类型，写入模型、关联关系和配置文件 |
| **3. 构建与验证** | 确认查询能端到端运行 | `janus context build`、`janus memory index`，通过引擎运行示例 SQL，而不仅仅是生成文件 |
| **4. 交付** | 展示第一批结果 | 运行几条有代表性的查询，并把结果展示给用户 |

用户可以从任一阶段开始。如果他们已经有之前 dlt 运行生成的 `.duckdb` 文件，该 Skill 可以直接从第 2 阶段开始。

内省脚本不是内联的，而是单独获取：

```bash
janus skills get dlt-connector --script introspect_dlt > introspect_dlt.py
python introspect_dlt.py --duckdb-path ./pipeline.duckdb --output-dir ./project
```

### 两条不可协商的约束

1. **DuckDB catalog 命名**：当 Janus AI `ATTACH` 一个 `.duckdb` 文件时，它会使用文件名（不含扩展名）作为 catalog 别名。因此每个模型的 `table_reference.catalog` **必须等于文件名（不含扩展名）**。
   `stripe_data.duckdb` 对应的 catalog 为 `stripe_data`。内置的 `introspect_dlt` 脚本会自动处理这一点，切勿手动覆盖。
2. **通过 janus SDK 规范化类型**：列类型必须经过 `janus.type_mapping.parse_type()`（基于 sqlglot）。不要硬编码映射；`HUGEINT` 或 `TIMESTAMP WITH TIME ZONE` 等 DuckDB 特有的类型需要转换为标准形式。

### 触发时机

发现存根在以下类似表述出现时，会把智能体路由到这里：

- "connect HubSpot / Stripe / Salesforce / GitHub / Slack data"
- "load data from a SaaS API"
- "import data from a REST API"
- "set up a dlt pipeline"
- "I have a `.duckdb` file from dlt — make a Janus project from it"

### 数据源覆盖范围

该 Skill 内置了一份常见的 dlt 已验证数据源参考列表，包括认证方式。对于不在列表中的数据源，智能体会先查阅 [dlthub.com/docs/dlt-ecosystem/verified-sources](https://dlthub.com/docs/dlt-ecosystem/verified-sources)，然后再尝试自行处理。

---

## creport

把项目的上下文层转换为可分享的浏览器端 CReport Web 应用（由 `janus-core-wasm` 驱动），并部署到 Vercel 或 Cloudflare Pages。从一条自然语言请求到一个公开 URL，只需一次对话。完整命令参考：[`janus creport`](cli.md#janus-creport--build--deploy-creport-apps)。

### CLI 与智能体的分工

CLI 负责权威的构建说明和所有确定性状态（应用索引、verify、deploy）；智能体按照说明编写应用代码。`.janus/apps.yml` 只会由 CLI 写入。

### 工作流

| 步骤 | 目标 | 关键操作 |
|------|------|-------------|
| **1. 构建** | 获取权威的构建说明 | `janus creport build <name> --prompt "…" --data-mode snapshot\|live`，输出 wasm 接入方式（固定版本）、模型和列清单、验收标准以及目标目录 |
| **2. 编写** | 编写应用 | 智能体按照说明编写 `apps/<name>/`；复制 `mdl.json`；把快照数据导出为 `data/*.parquet`（基于 DuckDB 的项目，包括 dlt 的输出，导出都很简单） |
| **3. 注册并验证** | 记录并预检 | `janus creport register <name> --data-mode <mode>`，然后 `janus creport verify <name>`（文件、可解析的 MDL、快照资产、默认拒绝的密钥扫描） |
| **4. 预览** | 本地检查 | `janus creport open <name>` 在本地提供应用以供审阅 |
| **5. 部署** | 发布 URL | `janus creport deploy <name> --provider vercel\|cloudflare [--prod]`，默认部署为预览；使用 `--prod` 前需要确认 |

### 数据模式

- **snapshot**（默认）：数据随应用一起分发（parquet/duckdb），在客户端查询。完全无服务器，适合演示、报告、小数据量以及 dlt 管道的输出。
- **live**：应用在查看时调用支持 CORS 的端点。适合生产级规模或需要始终最新的数据；绝不内嵌凭据。

### 部署说明

- **令牌**来自环境变量或 `.env`（`VERCEL_TOKEN` / `CLOUDFLARE_API_TOKEN`，以及 `CLOUDFLARE_ACCOUNT_ID`），绝不通过 CLI 参数传递。
- **Cloudflare** 会调用 `wrangler` CLI（`npm install -g wrangler`）。
- **Vercel Deployment Protection** 默认开启：在 Project → Settings → Deployment Protection 中关闭之前，部署后的 URL 对未登录的访问者会返回 401。智能体会在称其可以分享之前，先验证该 URL 确实能够加载。

### 触发时机

发现存根在以下类似表述出现时，会把智能体路由到这里：

- "build a dashboard from my Janus project"
- "make a shareable analytics app"
- "deploy my context layer as a web app"
- "host a CReport app on Vercel / Cloudflare Pages"

### 数据来源衔接

如果数据来自 SaaS 数据源，请先运行 [`dlt-connector`](#dlt-connector)：它的 DuckDB 输出正是 `creport` 所打包的快照数据源。

---

## Skill 包结构

在 wheel 包内，每个 Skill 都是 `src/janus/skills_content/` 下的一个目录：

```text
src/janus/skills_content/
├── onboarding/
│   └── SKILL.md
├── usage/
│   ├── SKILL.md
│   └── references/
│       ├── memory.md
│       └── janus-sql.md
├── generate-mdl/
│   └── SKILL.md
├── enrich-context/
│   ├── SKILL.md
│   └── references/
│       ├── gap_catalog.md
│       └── cube_proposals.md
└── dlt-connector/
    ├── SKILL.md
    ├── references/
    │   └── dlt_sources.md
    └── scripts/
        └── introspect_dlt.py
```

每个 `SKILL.md` 都带有 YAML frontmatter，包括 name、description 和 license。`janus skills get <name>` 输出 `SKILL.md`；`--full` 会按排序追加每个 `references/*.md`；`--script <stem>` 输出 `scripts/` 中的单个文件。Skill 包通过 Hatchling 的 `[tool.hatch.build.targets.wheel] artifacts` 通配规则打包进 `janusai` wheel，因此全新安装的 `pip install janusai` 始终包含与之匹配的 Skill 内容。

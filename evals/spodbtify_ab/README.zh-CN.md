# Spodbtify A/B 评测

🌐 [English](./README.md) · **简体中文**

本评测比较两种工作流：将同一个 DuckDB 数据库转换为可查询的 Janus 语义层，然后对 AI 编码智能体回答 20 个 Spotify 歌单分析问题的表现进行打分。

本评测刻意与智能体无关。它并不绑定 Claude Code：任何能够读取 prompt 文件并写出答案文件的运行器，例如 Claude、Codex、Cursor、MCP 客户端，都可以使用同一份规范。

## 数据集

预期的本地数据集：

```bash
export SPODBTIFY_DUCKDB_PATH=/path/to/spodbtify.duckdb
```

预期的 dbt 项目产物：

```bash
export SPODBTIFY_DBT_PROJECT_DIR=/path/to/spodbtify-dbt-project

$SPODBTIFY_DBT_PROJECT_DIR/target/manifest.json
$SPODBTIFY_DBT_PROJECT_DIR/target/catalog.json
$SPODBTIFY_DBT_PROJECT_DIR/target/run_results.json
$SPODBTIFY_DBT_PROJECT_DIR/target/compiled/
```

该数据集刻意不纳入本仓库。

## 文件

- `spodbtify_ab_eval.json` 是权威的评测规范：包括工作流、对照组、表清单、评分标准、问题以及结果 schema。
- `agent_output.schema.json` 是可选的 JSON Schema，供支持结构化输出的智能体使用。
- `run_eval.py` 用于校验规范、生成 prompt、运行任意智能体命令模板，以及汇总评分文件。

## 快速校验

```bash
python3 evals/spodbtify_ab/run_eval.py validate
```

## 生成 Prompt

打印一条 prompt：

```bash
python3 evals/spodbtify_ab/run_eval.py prompt \
  --agent codex \
  --workflow dbt_integrated \
  --question 1
```

在不运行智能体的情况下，为所有问题生成 prompt 文件：

```bash
python3 evals/spodbtify_ab/run_eval.py run-agent \
  --agent codex \
  --workflow both \
  --dry-run
```

## 使用任意智能体 CLI 运行

`run-agent` 接受一个 shell 命令模板。可用的占位符如下：

- `{prompt_file}`
- `{output_file}`
- `{agent}`
- `{workflow}`
- `{question_id}`
- `{schema_file}`

示例形式：

```bash
python3 evals/spodbtify_ab/run_eval.py run-agent \
  --agent codex \
  --workflow schema_only \
  --command 'codex exec --sandbox danger-full-access --output-schema {schema_file} -o {output_file} - < {prompt_file}'
```

对于 Claude 或其他智能体，请使用等效的命令：

```bash
python3 evals/spodbtify_ab/run_eval.py run-agent \
  --agent claude \
  --workflow dbt_integrated \
  --command 'claude -p "$(cat {prompt_file})" > {output_file}'
```

具体的 CLI 参数因工具和安装方式而异。评测的约定是：输入 prompt 文件，输出答案文件。每个工作流请使用一个全新的会话，并且不要在工作流之间共享答案或记忆。

## 评分约定

智能体应返回如下 JSON：

```json
{
  "question_id": 1,
  "workflow": "dbt_integrated",
  "agent": "codex",
  "selected_tables": ["Top_Artists", "Artist_Collaborators"],
  "sql": "SELECT ...",
  "answer": "The analytical answer...",
  "notes": "Optional caveats"
}
```

在人工或外部评分者为每个问题分配 0/1/2 三项分数后，请使用以下命令所示的分数 schema 进行存储：

```bash
python3 evals/spodbtify_ab/run_eval.py new-score-template \
  --agent codex \
  --workflow dbt_integrated \
  --output /tmp/codex-dbt-score.json
```

然后进行汇总：

```bash
python3 evals/spodbtify_ab/run_eval.py score --scores /tmp/codex-dbt-score.json
```

请勿提交智能体的答案文件、运行目录或已评分的结果文件。

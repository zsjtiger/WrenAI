# 技能编写指南

🌐 [English](./AUTHORING.md) · **简体中文**

> **新技能内容应在何处编写：**
> **不在这里的 `skills/` 下。** 新的技能指南作为 Python 包数据发布，位于 [`core/janus/src/janus/skills_content/<name>/`](../core/janus/src/janus/skills_content/)，并通过 `janus skills get <name>` 在运行时提供。这使内容与已安装的 `janus` CLI 版本保持一致 —— 没有技能缓存，也没有 `versions.json` 漂移的变通方案。
>
> 本 `skills/` 目录树仅包含 AI 客户端安装的**发布桩**（一个新的发现桩 `janus/`，外加为保留一个版本而暂留的五个已弃用重定向桩）。

技能内容的格式仍遵循 [Agent Skills](https://agentskills.io/) 开放规范 —— 唯一的变化在于文件的存放位置，以及它们如何抵达智能体。

---

## 目录结构（位于 `core/janus/src/janus/skills_content/` 下）

```text
<name>/
├── SKILL.md              # Required — frontmatter + workflow instructions
├── references/           # Optional — reference docs, served by `janus skills get <name> --full`
│   ├── some-topic.md
│   └── another-topic.md
└── scripts/              # Optional — bundled scripts, served by `janus skills get <name> --script <s>`
```

---

## Frontmatter

```yaml
---
name: <name>              # matches the parent directory; lowercase, hyphens
description: "What this skill does and when to trigger it. Include trigger
  keywords so an AI client can match it to user intent."
license: Apache-2.0
metadata:
  author: janusai
---
```

**去掉 `version:` 字段。** 内容版本即已安装的 janusai 版本，因为 SKILL.md 随 wheel 一同发布。

---

## 渐进式披露

| 层级 | 内容 | 加载时机 |
|------|------|----------|
| 1 — 发现桩 | `skills/janus/SKILL.md` 的 frontmatter description（约几百个 token） | 每次 AI 客户端会话开始时 |
| 2 — 主指南 | `janus skills get <name>` | 智能体在用户任务与之匹配时运行该命令 |
| 3 — 参考资料 | `janus skills get <name> --full` | 智能体在需要更深入的内容时主动选择 |
| 3 — 脚本 | `janus skills get <name> --script <s>` | 同上 |

请将 `SKILL.md` 控制在约 500 行以内。仅供参考的内容请移到 `references/` 中。

---

## 内容的归属

### 保留在 `SKILL.md` 中
- 智能体需遵循的分步工作流
- 决策标准和分支逻辑
- 智能体需要立即使用的简短命令
- 快速参考表（文件路径、阶段映射等）

### 移到 `references/` 中
- 输出模板（报告格式、计划文件格式）
- 针对单个案例的调查细节
- 大型查找表
- 任何会使 `SKILL.md` 超过约 500 行的内容

在同一技能内部按参考名称进行交叉链接（通过 `--full` 提供）：
```markdown
For the CTE rewrite pipeline, see the `janus-sql` reference (run
`janus skills get usage --full`).
```

通过 CLI 命令交叉链接到另一个技能：
```markdown
For day-to-day querying after setup, run `janus skills get usage`.
```

交叉链接到通用文档：
```markdown
For troubleshooting, see [`connect.md`](https://github.com/CrossNow/JanusAI/blob/main/docs/core/guides/connect.md).
```

---

## 命名

| 项目 | 约定 | 示例 |
|------|------|------|
| 技能目录 | `kebab-case` | `generate-mdl/` |
| `name` 字段 | 与目录相同 | `generate-mdl` |
| 参考文件 | 描述性的 `kebab-case` | `memory.md`, `janus-sql.md` |
| 脚本文件 | 描述性的 `kebab-case` | `introspect_dlt.py` |

---

## 注册新技能

1. 在 `core/janus/src/janus/skills_content/<name>/` 下创建目录，并包含 `SKILL.md`（以及可选的 `references/`、`scripts/`）。
2. 按照上述格式编写内容。
3. 在 `core/janus/tests/unit/test_skills_cli.py` 中添加一个测试，验证 `janus skills get <name>` 能返回指南，并且 `--full` 会内联其参考资料（如果有）。
4. 完成 —— 无需更新单独的 `versions.json` / `index.json`；包数据随 wheel 一同发布，`janus skills list` 会自动枚举它。

无需执行 `bash skills/check-versions.sh` 步骤 —— 版本漂移从构造上就不可能发生（内容随二进制文件一同分发）。

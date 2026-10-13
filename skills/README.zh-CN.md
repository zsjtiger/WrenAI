# Janus 引擎 — Agent Skill 分发

🌐 [English](./README.md) · **简体中文**

技能的实际内容（工作流指南、参考文档和提示辅助工具）**位于 `janus` CLI 内部**。本目录仅提供一个发现用的桩（stub）文件，AI 客户端安装一次即可；该桩文件会告诉智能体在运行时从 CLI 获取其余所有内容（因此内容始终与已安装的 janusai 版本保持一致）。

完整的设计和命令接口请参见 [`SKILLS.md`](SKILLS.zh-CN.md)。

## 安装

### CLI 本身（所有技能内容都在这里）

```bash
pip install janusai
```

### 发现桩（让 AI 客户端知道 CLI 的存在）

#### 方式 1 — Claude Code 插件

```text
/plugin marketplace add CrossNow/JanusAI --path skills
/plugin install janus@janus
```

#### 方式 2 — `npx skills`

```bash
npx skills add CrossNow/JanusAI
```

安装程序会自动检测你的 AI 客户端。如需指定某个客户端，请添加 `--agent <name>`（例如 `claude-code`、`cursor`、`windsurf`、`cline`）。

#### 方式 3 — 本地安装脚本

```bash
bash skills/install.sh                 # install the discovery stub
bash skills/install.sh --force         # overwrite existing
```

## 智能体如何处理该桩

安装后，智能体会读取 `janus/SKILL.md`，并学会调用：

```bash
janus skills list                        # discover workflow guides
janus skills get onboarding              # fetch a guide (one of 5 names)
janus docs connection-info <ds>          # connection fields for a data source
janus ask "<question>" --guided|--direct # wrap a prompt for an agent
```

## 要求

- 已安装 `janus` CLI（`pip install janusai` 或 `pip install "janusai[<extras>]"`）
- 数据库连接（通过 `janus profile add` 配置）
- 支持技能的 AI 客户端（Claude Code、Cursor、Cline 等）

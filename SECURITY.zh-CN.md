🌐 [English](./SECURITY.md) · **简体中文**

# 安全策略

## 报告漏洞

如果你认为在任何 Canner 所属的代码仓库中发现了安全漏洞，请通过协调披露（coordinated disclosure）的方式向我们报告。

**请不要通过公开的 GitHub issue、讨论或 Pull Request 报告安全漏洞。**

请发送邮件至 `contact@cannerdata.com`。

请尽可能多地提供以下信息，以帮助我们更好地理解并解决问题：

- 问题类型（例如缓冲区溢出、SQL 注入、跨站脚本）
- 与问题表现相关的源文件完整路径
- 受影响源代码的位置（标签/分支/提交，或直接 URL）
- 复现问题所需的任何特殊配置
- 复现问题的分步说明
- 概念验证或利用代码（如有）
- 问题的影响，包括攻击者可能如何利用它

这些信息将有助于我们更快地对报告进行分类处理。

## 支持的版本

安全修复仅发布在每个已发布包（`janusai`、`janus-core`、`janus-core-wasm`）的最新次要版本上。较旧的版本可能会尽力修补。

历史遗留的 JanusAI CReport 应用（保存在 `legacy/v1` 分支，标签 `v1-final`）在冻结之后**不再**接收安全更新。新的部署请使用维护中的 [`main`](https://github.com/CrossNow/JanusAI/tree/main) 分支。

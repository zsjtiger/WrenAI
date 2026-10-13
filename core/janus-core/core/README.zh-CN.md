# janus-semantic-core
🌐 [English](./README.md) · **简体中文**

[Janus AI](https://crossnow.cn) 的 Rust 语义引擎核心 —— 一个面向 MCP 客户端和 AI 智能体的开源语义层。

`janus-semantic-core` 接收一个 **MDL（Modeling Definition Language，建模定义语言）** manifest 以及一条 SQL 查询，并通过语义层对查询进行改写：解析模型、关系、指标和视图，应用行级与列级访问控制，最终生成优化后的逻辑计划。它基于 [Apache DataFusion](https://datafusion.apache.org/) 构建。

> 发布的 crate 名称为 `janus-semantic-core`；库本身的导入名称为 `janus_core`。

## 安装

```toml
[dependencies]
janus-semantic-core = "0.1"
```

## 用法

```rust
use janus_core::mdl::AnalyzedJanusMDL;
// Build an AnalyzedJanusMDL from a manifest, then transform SQL through the
// semantic layer. See the API docs for the full flow.
```

完整的 API 文档发布在 [docs.rs](https://docs.rs/janus-semantic-core) 上。

## 功能概述

- **MDL 分析** —— 将 manifest 解析为模型、列、指标、关系和视图。
- **查询规划** —— 基于语义层将传入的 SQL 改写为 DataFusion 逻辑计划，解析关系链并展开视图。
- **访问控制** —— 应用行级（RLAC）和列级（CLAC）访问规则。
- **优化** —— 类型强制转换和时间戳简化等优化步骤。

## 了解更多

- Janus 文档：<https://docs.crossnow.cn>
- 项目主页：<https://crossnow.cn>
- 源代码：<https://github.com/CrossNow/JanusAI>

## 自定义访问控制

默认的 `JanusAccessControlProvider` 会评估 MDL 的行规则和列规则。
Rust 应用可以实现 `AccessControlProvider`，并将 `Arc<dyn AccessControlProvider>` 传递给 `mdl::transform_sql_with_ctx_with_access_control` 以替换默认 provider。查询规划和权限错误诊断使用同一个 provider。现有的 transform 函数仍然使用 MDL provider。

对于远程 SQL 生成，首先调用 `AnalyzedJanusMDL::analyze_with_unfiltered_schema` 来推断物理列，此时不应用 MDL 列规则。这一步只准备 schema 和血缘信息，**并不**授权查询。对于本地注册的表，请使用 `analyze_with_tables`。然后通过支持 provider 的 transform 函数，或通过 `mdl::context::apply_janus_on_ctx_with_access_control`（用于直接的 DataFusion 规划）应用所选的 provider。配置了自定义 provider 的上下文不能传给默认的 transform 函数并期望它保留该 provider：默认函数会使用 MDL 规则重新配置访问控制。

provider 提供以下内容：

- `row_filter`：可选的 DataFusion 表达式，作用于语义模型的列。返回错误会拒绝整个模型；`None` 表示不做行限制。
- `column_access`：`Allow` 或 `Deny { rule_name }`。被拒绝的列会从通配符中省略；显式引用则会产生权限错误。
- `collect_required_fields`：求值行过滤器所需的该模型列，即使这些列不在用户的投影中。这些列同样会经过列检查，且不会成为额外的用户可见结果列。

`AccessScope::DirectQuery` 包含用户自己编写的子查询。`InternalSubquery` 保留给由 provider 的行过滤器引入的子查询；这些子查询会使用同一 provider 递归分析。provider 必须支持并发调用，且不得共享可变的查询遍历状态。在 provider 求值之前，属性会被规范化为小写键。provider 出错会停止规划，而不会切换到其他 provider。

该 Rust 扩展 API 不包含列脱敏功能，也没有 Python/JavaScript provider 注册 API。应用程序仍需负责对其 provider 所绑定的身份进行认证。

完整的可运行示例请参阅 [`custom-access-control.rs`](../janus-example/examples/custom-access-control.rs)。在 `core/janus-core` 工作区中运行 `cargo run -p janus-example --example custom-access-control` 即可执行。

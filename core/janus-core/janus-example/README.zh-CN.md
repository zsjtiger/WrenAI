# Janus 引擎示例
🌐 [English](./README.md) · **简体中文**

本 crate 包含多个示例，展示了如何使用 Janus 引擎 API，帮助你快速上手。

## 运行示例

使用 `cargo run` 命令运行示例，例如：

```bash
git clone https://github.com/CrossNow/JanusAI.git
cd JanusAI/core/janus-core

# Run the `datafusion_apply` example:
# ... use the equivalent for other examples
cargo run --example datafusion-apply
```

## 单进程
- [`datafusion-apply.rs`](examples/datafusion-apply.rs)：将建模定义语言（MDL）应用于 DataFusion，以查询本地 CSV 文件
- [`plan_to_sql.rs`](examples/plan_to-sql.rs)：应用 MDL，从 DataFusion 的 `Expr` 和 `LogicalPlan` 生成 SQL

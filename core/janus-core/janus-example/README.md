# Janus Engine Examples
🌐 **English** · [简体中文](./README.zh-CN.md)
The crate includes several examples of how to use Janus Engine APIs and help you on your way.

## Running Examples

To run the examples, use the `cargo run` command, such as:

```bash
git clone https://github.com/CrossNow/JanusAI.git
cd JanusAI/core/janus-core

# Run the `datafusion_apply` example:
# ... use the equivalent for other examples
cargo run --example datafusion-apply
```

## Single Process
- [`datafusion-apply.rs`](examples/datafusion-apply.rs): Apply an Modeling Definition Language(MDL) to a DataFusion to query local CSV files
- [`plan_to_sql.rs`](examples/plan-sql.rs): Apply an Modeling Definition Language(MDL) to generate SQL from Datafusion `Expr` and `LogicalPlan`
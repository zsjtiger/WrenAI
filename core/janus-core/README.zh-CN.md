# Janus Core 模块
🌐 [English](./README.md) · **简体中文**

Janus Core 模块是 Janus 引擎的语义核心。要了解 Janus 引擎的概念，请参阅 [Janus 引擎文档](https://docs.crossnow.cn/oss/engine/concept/what_is_semantics)。

本模块被 ibis-server 的 API v3 用于 SQL 规划。此外，还有一个用于 Python 绑定的模块 [janus-core-py](../janus-core-py/)，同样被 ibis-server 使用。

## 如何测试 / 构建

- **运行测试**：
  - 大多数单元测试位于 `src/mdl/mod.rs` 中。
  - SQL 端到端测试通过 `sqllogictests` 执行。

可以使用以下命令运行所有测试：
```
cargo test
```


## 代码风格

提交 Pull Request 前请确保代码已正确格式化。Rust 文件使用 `rustfmt` 格式化，TOML 文件使用 `taplo` 格式化。

### 使用 rustfmt 格式化

运行以下命令格式化 Rust 代码：

```
cargo fmt
```

### 使用 taplo 格式化 TOML

安装 `taplo-cli`，然后使用以下命令格式化 TOML 文件：

```
cargo install taplo-cli --locked
taplo fmt
```

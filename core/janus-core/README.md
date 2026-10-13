# Janus Core Module
🌐 **English** · [简体中文](./README.zh-CN.md)

The Janus Core module serves as the semantic core of the Janus engine. To understand the concept of the Janus engine, refer to the [Janus engine documentation](https://docs.crossnow.cn/oss/engine/concept/what_is_semantics). 

This module is utilized by the API v3 of the ibis-server for SQL planning. Additionally, there is another module for Python bindings, [janus-core-py](../janus-core-py/), which is also used by the ibis-server.

## How to Test / Build

- **Run Tests**:
  - Most unit test cases are located in `src/mdl/mod.rs`.
  - SQL end-to-end tests are executed using `sqllogictests`.

You can run all tests with the following command:
```
cargo test
```


## Coding Style

Please ensure your code is properly formatted before submitting a pull request. Use `rustfmt` for Rust files and `taplo` for formatting TOML files.

### Format with rustfmt

Run the following command to format Rust code:

```
cargo fmt
```

### Format TOML with taplo

Install `taplo-cli` and format TOML files with the following commands:

```
cargo install taplo-cli --locked
taplo fmt
```
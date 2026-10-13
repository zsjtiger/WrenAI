# 为 JanusAI 做贡献

🌐 [English](./CONTRIBUTING.md) · **简体中文**

感谢你对本项目的贡献感兴趣。我们欢迎 Pull Request、Bug 报告和讨论。

## 开始之前

- 请阅读 **[行为准则](./CODE_OF_CONDUCT.zh-CN.md)** —— 它适用于所有项目空间。
- 对于 Bug 或功能请求，请先搜索[已有 issue](https://github.com/CrossNow/JanusAI/issues)；对于开放式的想法，请使用 [Discussions](https://github.com/CrossNow/JanusAI/discussions)。
- 对于较大的改动，请在编码前先开启讨论，以便我们就方向达成一致。

## 各模块的开发

`core/` 下的每个模块都有各自的开发环境配置。请先阅读模块自己的 `README.md`：

| 模块 | 入口 | 技术栈 |
|---|---|---|
| [`core/janus-core/`](./core/janus-core) | `cargo check && cargo test` | Rust + DataFusion |
| [`core/janus-core-base/`](./core/janus-core-base) | `cargo test` | Rust |
| [`core/janus-core-py/`](./core/janus-core-py) | `just install && just test` | PyO3 + Maturin |
| [`core/janus-core-wasm/`](./core/janus-core-wasm) | `just build && just test` | wasm-pack |
| [`core/janus/`](./core/janus) | `just install && just test` | Python + uv |
| [`skills/`](./skills) | 参见 `skills/AUTHORING.md` | CLI 技能编写 |

## 约定

- **提交信息**：使用 [conventional commits](https://www.conventionalcommits.org/)（`feat:`、`fix:`、`chore:`、`refactor:`、`test:`、`docs:`、`perf:`、`deps:`）。发布通过 release-please 自动完成，每个模块拥有独立的发布线。
- **Rust**：使用 `cargo fmt` 格式化，使用 `clippy -D warnings` 进行 lint，使用 `taplo` 格式化 `Cargo.toml`。
- **Python**：使用 `ruff` 进行格式化和 lint（行宽 88，目标版本 Python 3.11）。`core/janus-core-py` 和 `core/janus` 都使用 `uv`。
- **测试**必须通过，并且 lint 必须干净，才能进入评审。CI 按模块进行路径过滤。

## 贡献的许可

提交 Pull Request 即表示你同意，你的贡献将按照其所修改路径所适用的相同条款授权：

- 对 **`core/**`、`skills/**`、`sdk/**`、`examples/**`** 以及**根目录文件**的贡献，依据 [Apache License 2.0](./LICENSE-APACHE-2.0) 授权。
- 对 **`docs/**`** 的贡献，依据 [知识共享署名 4.0 国际许可协议（CC BY 4.0）](./LICENSE-CC-BY-4.0) 授权。

如果未来某个模块采用 [AGPL-3.0](./LICENSE-AGPL-3.0) 许可，则对该路径的贡献将相应授权。权威的路径与许可证对应关系，请参见 [LICENSE](./LICENSE)。

## 报告安全问题

请**不要**为安全漏洞公开提交 issue。请改为发送邮件至 `contact@cannerdata.com`。详情请参见 [SECURITY.md](./SECURITY.zh-CN.md)。

# Janus Core Python 绑定

🌐 [English](./README.md) · **简体中文**

[janus-core](../janus-core) 的 Python 绑定。janus-core 是 [Janus Engine](https://github.com/CrossNow/JanusAI) 背后的 Rust 语义引擎。使用 [PyO3](https://github.com/PyO3/pyo3) 和 [Maturin](https://github.com/PyO3/maturin) 构建。

Janus Engine 通过语义层（MDL - Modeling Definition Language）转换 SQL 查询，并在 22+ 种数据源（PostgreSQL、BigQuery、Snowflake 等）上执行。

## 安装

```bash
pip install janus-core-py
```

需要 Python >= 3.11。

以下平台提供预构建 wheel：
- Linux x86_64 / ARM64（manylinux）
- macOS x86_64 / ARM64（Apple Silicon）
- Windows x86_64

在其他平台上，pip 会回退到 sdist 并从源码构建，这需要 Rust 工具链。

## 快速开始

```python
from janus_core import SessionContext

# 从 base64 编码的 MDL JSON 字符串创建会话上下文
base64_mdl_json = "<your-base64-encoded-mdl-json>"
ctx = SessionContext(base64_mdl_json)

# 通过语义层转换 SQL 查询
planned_sql = ctx.transform_sql("SELECT * FROM my_model")
```

### 注册本地文件（Parquet/CSV）

物理文件可以通过两阶段初始化支持 MDL 模型——先注册文件，再加载 MDL，使模型解析到这些文件：

```python
from janus_core import SessionContext

base64_mdl_json = "<your-base64-encoded-mdl-json>"

ctx = SessionContext()
ctx.register_parquet("customer", "/data/customer.parquet")
ctx.register_csv("orders", "/data/orders.csv")
ctx.load_mdl(base64_mdl_json)  # MDL 模型现在会解析到这些文件

# 通过 MDL 的 catalog.schema.model 名称查询；返回 Arrow IPC 流字节
ipc_bytes = ctx.query("SELECT * FROM my_catalog.my_schema.customer")
```

可见性约定：

- 表会注册到已存在的默认 catalog（`datafusion`.`public`）中。只有当某个 MDL 模型的 `tableReference` 为 `{"catalog": "datafusion", "schema": "public", "table": "<registered name>"}` 且其声明的列在文件中存在时，该模型才会解析到已注册的文件。
- 在 context 创建之后再注册依然有效：已存在的 catalog 的内部状态会与派生 context 实时共享，因此该表对 `query`、`dry_run` 和 `list_tables` 可见。
- 全新的*顶层* catalog 是例外——它们必须在 MDL 构建、`load_mdl` 或任何 transform 之前存在，因为这些操作都会对顶层 catalog 列表做快照。
- 关于 `load_mdl` 的重叠规则，参见下方的并发一节。

完整的可运行示例（夹具文件、匹配的清单、解码返回的字节）参见 `tests/test_physical_tables.py`。

### 并发

同一个 `SessionContext` 上的调用并行运行。每个 `transform_sql` 都在私有的顶层 catalog 快照上工作，分析器状态按每次调用隔离，因此受支持的并发调用不会观察到彼此的中间状态。约定如下：

- 对于 `transform_sql` 和 `query` 接受的只读输入以及注册 API，支持并发执行。`dry_run` 对于仅由 `EXPLAIN` 规划的语句是并发安全的。以 `ANALYZE` 为前缀的输入会变为 `EXPLAIN ANALYZE` 并执行；与 `query()` 接受的会修改状态的语句一样，它不在并发约定范围内。函数查找方法是只读的，并且并发安全。
- `register_parquet` / `register_csv` 在表名不同时是安全的；并发注册同名表不受支持。
- `list_tables` 是尽力而为的枚举：调用期间完成的注册可能出现也可能不出现，但结果始终格式良好。
- `load_mdl` 不得与同一 context 上的其他调用重叠；重叠调用会抛出 `RuntimeError`。

## 开发者指南

### 环境搭建

- 安装 [Rust](https://www.rust-lang.org/tools/install) 和 [Cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html)
- 安装 [Python](https://www.python.org/downloads/)
- 安装 [uv](https://github.com/astral-sh/uv)
- 安装 [casey/just](https://github.com/casey/just)

### 测试与构建

安装 `casey/just` 后，可以使用以下命令：

- `just install` — 创建 Python 虚拟环境并安装依赖。
- `just develop` — 为本地开发构建 Rust 包（**运行 Python 测试前必需**）。
- `just test-rs` — 仅运行 Rust 测试。
- `just test-py` — 仅运行 Python 测试。
- `just test` — 同时运行 Rust 和 Python 测试。
- `just build` — 构建 Python wheel。输出到 `target/wheels/`。

### 代码风格

使用 `just format` 进行格式化。

### 发布

本地发布到 PyPI/TestPyPI 请参见 `scripts/publish.sh`：

```bash
./scripts/publish.sh --build    # 仅构建 wheel
./scripts/publish.sh --test     # 构建并发布到 TestPyPI
./scripts/publish.sh            # 构建并发布到 PyPI
```


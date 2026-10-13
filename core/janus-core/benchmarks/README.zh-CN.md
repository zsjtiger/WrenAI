# Janus Core 基准测试
🌐 [English](./README.md) · **简体中文**

本 crate 包含 Janus core 库的基准测试。这些测试基于业界标准的开源基准测试构建，旨在帮助衡量和提升 Janus core 的性能。

# 支持的基准测试

## TPC-H

TPC-H 基准测试使用标准的决策支持查询来衡量查询性能。

本基准测试派生自 [TPC-H][1] 的 [2.17.1] 版本。数据和参考答案由 [2] 中的 `tpch-gen` 生成。

[1]: http://www.tpc.org/tpch/
[2]: https://github.com/databricks/tpch-dbgen.git
[2.17.1]: https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v2.17.1.pdf

## Janus

本基准测试用于收集复杂的 SQL 测试用例，以评估 Janus AI 的性能。

- **`q1`**：一个包含多个 CTE（公共表表达式）和子查询的复杂 SQL 查询，用于测试复杂的查询规划与优化。
- **`q2`**：与 `q1` 类似，但额外包含一个 `UNION` 子句，用于测试集合操作的查询改写与优化。

# 运行基准测试

## 使用 `bench.sh` 快速开始

运行基准测试最简单的方法是使用 [bench.sh](bench.sh) 脚本。要查看所有可用选项和用法说明：

```shell
# Show usage information
./bench.sh
```

## 分支之间的性能比较

要比较主分支与功能分支之间的性能：

```shell
# Switch to main branch and gather baseline data
git checkout main
./benchmarks/bench.sh run tpch

# Switch to your feature branch and gather comparison data
git checkout mybranch
./benchmarks/bench.sh run tpch

# Compare results between the two branches
./bench.sh compare main mybranch
```

比较结果将生成如下所示的详细性能报告：

```shell
Comparing main and mybranch
--------------------
Benchmark tpch.json
--------------------
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Query        ┃    main ┃mybranch ┃    Change ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ QQuery 1     │  4.25ms │  4.26ms │ no change │
│ QQuery 2     │ 11.25ms │ 11.68ms │ no change │
│ QQuery 3     │  5.03ms │  4.97ms │ no change │
│ QQuery 4     │  3.43ms │  3.46ms │ no change │
│ QQuery 5     │  7.39ms │  7.28ms │ no change │
│ QQuery 6     │  2.26ms │  2.26ms │ no change │
│ QQuery 7     │  8.53ms │  8.51ms │ no change │
│ QQuery 8     │  9.90ms │  9.99ms │ no change │
│ QQuery 9     │  8.56ms │  8.27ms │ no change │
│ QQuery 10    │  7.37ms │  7.63ms │ no change │
│ QQuery 11    │  7.06ms │  7.00ms │ no change │
│ QQuery 12    │  4.35ms │  4.19ms │ no change │
│ QQuery 13    │  2.93ms │  2.88ms │ no change │
│ QQuery 14    │  3.34ms │  3.33ms │ no change │
│ QQuery 15    │  6.51ms │  6.49ms │ no change │
│ QQuery 16    │  4.59ms │  4.64ms │ no change │
│ QQuery 17    │  4.00ms │  4.05ms │ no change │
│ QQuery 18    │  5.46ms │  5.47ms │ no change │
│ QQuery 19    │  5.84ms │  5.72ms │ no change │
│ QQuery 20    │  7.22ms │  7.33ms │ no change │
│ QQuery 21    │  9.35ms │  9.19ms │ no change │
│ QQuery 22    │  4.54ms │  4.33ms │ no change │
└──────────────┴─────────┴─────────┴───────────┘
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Benchmark Summary      ┃          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ Total Time (main)      │ 133.16ms │
│ Total Time (mybranch)  │ 132.92ms │
│ Average Time (main)    │   6.05ms │
│ Average Time (mybranch)│   6.04ms │
│ Queries Faster         │        0 │
│ Queries Slower         │        0 │
│ Queries with No Change │       22 │
└────────────────────────┴──────────┘
```

## 手动运行基准测试

如需更精细地控制基准测试的执行，可以直接使用 Cargo 运行单个基准测试：

```bash
# Run TPC-H benchmark for query 1 with 10 iterations, output to JSON
cargo run --release --bin tpch -- benchmark --query 1 -i 10 -o result.json

# Run all TPC-H queries
cargo run --release --bin tpch -- benchmark --all-queries -i 5

# Run Janus-specific benchmarks
cargo run --release --bin janus -- benchmark --query 1 -i 10
```

### 命令行选项

- `--query <number>`：运行指定的查询（TPC-H：1-22，Janus：1-2）
- `-i, --iterations <number>`：运行的迭代次数（默认：1）
- `-o, --output <file>`：将结果输出到 JSON 文件
- `--all-queries`：运行基准测试套件中所有可用的查询


## 项目结构

```
benchmarks/
├── bench.sh              # Main benchmark runner script
├── data/                 # Generated benchmark data
├── results/              # Benchmark results and comparisons
├── src/
│   ├── tpch/            # TPC-H benchmark implementation
│   └── janus/            # Janus-specific benchmark queries
└── Cargo.toml           # Dependencies and build configuration
```

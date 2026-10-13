---
sidebar_label: 使用 Cube 预聚合
---

# 使用 Cube 预聚合

Cube 是预聚合的语义对象：一个基础模型或视图，加上声明好的度量、维度、时间维度和层级。它们为智能体提供**结构化的聚合 API**，而不是让智能体手写 `GROUP BY`、`DATE_TRUNC` 和指标运算。这些 SQL 正是小型或本地模型最容易出错的地方。

## 完成后你会得到

- 每个 Cube 对应一个 `cubes/<name>/metadata.yml`，用于声明其度量和维度
- 在 MDL 中可查询的 Cube 名称，例如 `janus cube query --cube revenue --measures total --time-dimension "order_date:month"`
- 一个会选择结构化 Cube 查询、而不是自己编写聚合 SQL 的智能体

## 为什么这个原语很重要

智能体编写分析型 SQL 时，最常见的失败模式包括：

- 基于原始外键重建 join 时关联错误
- 在错误的粒度上聚合，导致重复计算
- 时间粒度不明确，导致日期截断错误
- 发明了一个与团队认可的定义不一致的指标

Cube 把这四类问题都收拢了：度量、维度、时间粒度和 join 路径只需声明一次。智能体只提供结构化输入，引擎负责生成正确的 SQL。

这是对小型模型而言**杠杆最高的正确性原语**，因为对小模型来说，"知道该问什么"和"能正确写出 SQL"之间的差距最大。

## 定义 Cube

Cube 位于 `cubes/<name>/metadata.yml`。下面是一个基于现有 `orders` 模型的简单 Cube：

```yaml
name: revenue
base_object: orders
measures:
  - name: total
    expression: SUM(amount)
    type: DOUBLE
  - name: order_count
    expression: COUNT(*)
    type: BIGINT
dimensions:
  - name: status
    expression: status
    type: VARCHAR
time_dimensions:
  - name: order_date
    expression: order_date
    type: DATE
hierarchies:
  time: [order_date]
```

`hierarchies` 是一个映射，键为层级名称，值为有序的已声明维度或时间维度名称列表。层级中的级别名称必须与 `dimensions` 或 `time_dimensions` 中的条目一致。

每个 Cube 字段的说明，请参见 [MDL Schema 参考](/oss/reference/mdl)。

## 查询 Cube

`janus cube query` 命令接受结构化输入：

```bash
janus cube query \
  --cube revenue \
  --measures total,order_count \
  --dimensions status \
  --time-dimension "order_date:month" \
  --filter "status:eq:completed"
```

`--time-dimension` 的格式为 `<name>:<granularity>`，`--filter` 的格式为 `<dimension>:<operator>:<value>`。完整的粒度和过滤运算符列表，请参见 [CLI 参考](/oss/reference/cli#janus-cube--pre-aggregation-queries)。

不需要手写 `GROUP BY`，不需要 `DATE_TRUNC`，也不需要推断 join。

## 何时添加 Cube

在以下情况添加 Cube：

- 某个指标被频繁查询（收入、留存、月活）
- 该指标有团队认可的明确定义（尚未定论的指标不要建模）
- 你技术栈中的小型或本地模型在聚合上表现不佳
- 你希望获得一个稳定的接口，使其能够在基础模型发生 Schema 漂移后依然可用

以下情况**不要**添加 Cube：

- 指标是探索性的或一次性的（直接写 SQL 查询即可）
- 指标定义仍有争议（先写入 `knowledge/rules/`）
- 没有明确的粒度（Cube 需要明确的度量和维度）

## 何时需要回到这里

- 你技术栈中的小型或本地模型开始产生幻觉式的聚合
- 你把一个指标从"在 Slack 中达成共识"提升为"写入 MDL"
- 一个新的业务 KPI 获得了正式批准
- 你希望通过 SDK 把某个指标暴露给面向客户的应用

## 另请参阅

- [MDL Schema 参考](/oss/reference/mdl)：完整的 Cube 字段参考，包括层级和预聚合
- [Janus AI 如何防止智能体产生幻觉？](/oss/concepts/correctness)：为什么 Cube 是正确性原语
- [为你的业务建模](./model.md)：Cube 之前的建模步骤

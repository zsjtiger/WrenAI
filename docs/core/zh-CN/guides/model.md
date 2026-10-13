---
sidebar_label: 为你的业务建模
---

# 为你的业务建模

把你的数据仓库 Schema 转换为智能体可读的 MDL 项目，并捕获你的业务逻辑。这是所有生成的答案和 CReport 仪表盘所依托的基础。

## 完成后你会得到

- 一个 Janus 项目目录，包含 `janus_project.yml`、`models/`、`views/`、`relationships.yml` 和 `knowledge/`
- 编译好的 `target/mdl.json`，可直接供引擎使用
- 基于建模 Schema 的记忆索引，使智能体能够为每个问题检索相关上下文
- 第一条通过 MDL 执行的查询，而不是直接查询原始表

## 流程

1. **连接你的数据源。** 配置文件的设置参见[连接你的数据](./connect.md)。
2. **在一个新的项目目录中打开你的智能体，并提问：**
   > 使用 `/janus` Skill 为这个数据库搭建 MDL 项目。
3. **审阅初始脚手架。** 智能体会检查 Schema、规范化类型、识别关联关系，并为每张表生成一个模型。遇到无法独自决定的问题时（命名、标准表、有歧义的外键），它会提出一个有针对性的问题。
4. **构建并建立索引。** Skill 完成时会执行：
   ```bash
   janus context build
   janus memory index
   ```
5. **运行第一条基于模型的查询。**
   ```bash
   janus --sql "SELECT * FROM customers LIMIT 5"
   ```

## 脚手架提供的内容

第一版比较粗糙，但可以正常工作。智能体会生成：

- **每个物理表对应一个模型**，并显式声明列（不使用 `SELECT *`，避免歧义）
- **类型规范化**：通过 `janus utils parse-type`，让 manifest 中的类型保持统一
- **主键和关联关系**：在连接器提供外键元数据的情况下，从中推断
- **一个空的 `knowledge/` 库**，供你填写业务规则（`knowledge/rules/`）

所有内容都是可以审阅和版本化的 YAML，没有任何内容被锁在 UI 中。

## 脚手架无法提供的内容

真正的业务含义存在于数据库之外。脚手架无法告诉你：

- `customers`、`customers_v3`、`loyalty_v3` 中哪一个是标准表
- 为什么 `status = 4` 表示已退款
- "活跃客户"是否排除了服务账号
- "Project Lighthouse" 对应 `campaign_id = 4172`

这些内容需要通过[提升回答质量](/oss/guides/refine)补充，这是一个通过追问（grill）或自动驾驶循环来填补语义空白的流程。

## 逐步丰富

建立基线之后，可以逐步增加深度：

- **模型和列的描述与业务名称**：记忆检索会使用这些内容
- **计算字段**：用于团队已达成一致的指标（如 `revenue = net_total - refunds`）
- **关联列**：让计算字段无需手写 join 即可从相关模型取值（参见 [关联列](/oss/reference/mdl#relationship-columns)）
- **视图**：用于稳定、预先构建好的查询形式（如 `completed_orders`、`monthly_revenue`）
- **Cube**：用于受治理的聚合（参见[使用 Cube 预聚合](./cubes.md)）
- **选择性暴露列**：让 PII 列对智能体不可见。从模型中去掉的列无法被查询

每次编辑后，都需要重新构建并建立索引：

```bash
janus context build
janus memory index
```

## 何时需要回到这里

- 新的表或新的业务域进入你的数据仓库
- Schema 漂移导致现有模型失效
- 团队确定了一个新的指标定义，值得从 `knowledge/rules/` 提升为计算字段
- AI 编码智能体建议了值得审阅的结构性修改

## 另请参阅

- [MDL Schema 参考](/oss/reference/mdl)：MDL 文件接受的每个字段
- [提升回答质量](/oss/guides/refine)：通过记忆和指令闭合反馈回路
- [MDL 为智能体做了什么？](/oss/concepts/what_is_mdl)：MDL 背后的设计理念

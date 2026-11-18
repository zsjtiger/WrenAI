# 权限的操作与使用：一个完整例子

本例用仓库里的 `core/janus/examples/access-roles/` 演示。数据是一个 DuckDB 文件，服务是 HTTP API。所有输出都来自实际运行。

## 场景

同一张 `orders` 表，两类人使用：

- **分析师**：只能看自己客户（`customer_id = 1`）的订单，看不到 `amount`。
- **经理**：看全部订单，包括 `amount`。

## 一、原始数据

由 `make_warehouse.py` 写入 DuckDB 文件 `warehouse.duckdb`：

```sql
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name VARCHAR, region VARCHAR);
INSERT INTO customers VALUES
  (1, 'Ada',  'APAC'),
  (2, 'Ben',  'EU'),
  (3, 'Chen', 'APAC'),
  (4, 'Dana', 'US');

CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER,
                     amount DECIMAL(10, 2), status VARCHAR);
INSERT INTO orders VALUES
  (101, 1, 120.00, 'shipped'),
  (102, 1,  35.50, 'shipped'),
  (103, 2, 480.00, 'pending'),
  (104, 3,  75.25, 'shipped'),
  (105, 4, 210.00, 'cancelled'),
  (106, 2,  18.90, 'shipped');
```

| customers | name | region |
|---|---|---|
| 1 | Ada | APAC |
| 2 | Ben | EU |
| 3 | Chen | APAC |
| 4 | Dana | US |

| order_id | customer_id | amount | status |
|---|---|---|---|
| 101 | 1 | 120.00 | shipped |
| 102 | 1 | 35.50 | shipped |
| 103 | 2 | 480.00 | pending |
| 104 | 3 | 75.25 | shipped |
| 105 | 4 | 210.00 | cancelled |
| 106 | 2 | 18.90 | shipped |

## 二、模型定义（`metadata.yml`）

两个模型由 `janus context draft --from-db` 生成，`orders` 的规则由 `add_rules.py` 加上。

### `models/customers/metadata.yml`

```yaml
name: customers
table_reference:
  catalog: warehouse
  schema: main
  table: customers
columns:
- name: customer_id
  type: INT
  is_calculated: false
  not_null: true
  is_primary_key: true
  properties: {}
- name: name
  type: TEXT
  is_calculated: false
  not_null: false
  is_primary_key: false
  properties: {}
- name: region
  type: TEXT
  is_calculated: false
  not_null: false
  is_primary_key: false
  properties: {}
cached: false
properties: {}
primary_key: customer_id
```

`customers` 没有访问规则。

### `models/orders/metadata.yml`

```yaml
name: orders
table_reference:
  catalog: warehouse
  schema: main
  table: orders
columns:
- name: order_id
  type: INT
  is_calculated: false
  not_null: true
  is_primary_key: true
  properties: {}
- name: customer_id
  type: INT
  is_calculated: false
  not_null: false
  is_primary_key: false
  properties: {}
- name: amount
  type: DECIMAL(10, 2)
  is_calculated: false
  not_null: false
  is_primary_key: false
  properties: {}
  column_level_access_control:
    name: amount_for_managers
    required_properties:
    - name: session_level
      required: true
    operator: GREATER_THAN_OR_EQUALS
    threshold: '2'
- name: status
  type: TEXT
  is_calculated: false
  not_null: false
  is_primary_key: false
  properties: {}
cached: false
properties: {}
primary_key: order_id
row_level_access_controls:
- name: own_or_manager
  required_properties:
  - name: session_customer
    required: true
  - name: session_level
    required: true
  condition: customer_id = @session_customer OR @session_level >= 3
```

### 字段说明

| 字段 | 含义 | 本例中的值 |
|---|---|---|
| `table_reference` | 映射到哪张数据库表 | `warehouse.main.orders` |
| `columns[].type` | 列类型，用于规划 | `DECIMAL(10, 2)` |
| `primary_key` | 主键 | `order_id` |
| `column_level_access_control` | 列级规则 | 限制 `amount` |
| `required_properties[].required` | 调用时是否必须提供 | 必须为 `true`，否则配置检查报错 |
| `operator` / `threshold` | 列规则的比较 | `>= 2` |
| `row_level_access_controls` | 行级规则，`condition` 中用 `@属性名` 引用会话属性 | 按 `customer_id` 与 `session_level` 过滤 |
| `properties` | 业务属性（术语、认证等） | 本例为空 |

## 三、角色与令牌（服务端配置）

`janus_access.yml` 由安全团队维护，放在服务端，不随项目发布。令牌值只写环境变量名：

```yaml
version: 1
roles:
  analyst:
    sql: SELECT 1 AS session_level, 1 AS session_customer
    allow_override: [session_customer]
  manager:
    sql: SELECT 3 AS session_level, 0 AS session_customer
    allow_override: []
tokens:
  - id: svc_analyst_app
    token_env: JANUS_TOKEN_ANALYST
    default_role: analyst
    may_request_role: false
    may_override: true
  - id: svc_bi_console
    token_env: JANUS_TOKEN_MANAGER
    default_role: manager
    may_request_role: true
    may_override: false
audit:
  path: work/access_audit.jsonl
  record_sql: true
```

角色的 `sql` 启动时执行一次，返回一行。列名就是会话属性名。

## 四、操作步骤

### 1. 检查配置

```bash
janus context build --path ./project
janus access report --path ./project --access-config janus_access.yml
```

实际输出：

```
role analyst  model orders
    rows: own_or_manager: customer_id = @session_customer OR @session_level >= 3
    denied: amount (session_level=1 fails GREATER_THAN_OR_EQUALS 2)
role manager  model orders
    rows: own_or_manager: customer_id = @session_customer OR @session_level >= 3
    columns: amount
ok: no errors or warnings
```

如果把 `session_level` 改成 `required: false`，报告会报错，服务不会启动。

### 2. 生成令牌并启动服务

```bash
export JANUS_TOKEN_ANALYST="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export JANUS_TOKEN_MANAGER="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
janus serve api --project ./project --port 8765 --access-config janus_access.yml
```

### 3. 调用并看结果

分析师查订单，只返回客户 1 的两条：

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_ANALYST" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id FROM orders ORDER BY order_id"}'
# 200：订单 101、102
```

分析师查 `amount`，列规则拒绝：

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_ANALYST" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id, amount FROM orders"}'
# 422：Permission Denied，访问列 "orders"."amount" 违反规则 "amount_for_managers"
```

分析师覆盖 `session_customer`（在允许列表中），看客户 2 的订单：

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_ANALYST" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id FROM orders ORDER BY order_id", "properties": {"session_customer": 2}}'
# 200：订单 103、106
```

分析师覆盖 `session_level`（不在允许列表中）：

```bash
  -d '{"sql": "SELECT order_id FROM orders", "properties": {"session_level": 3}}'
# 403：{"code": "override_not_allowed"}
```

分析师试图选角色：

```bash
  -d '{"sql": "SELECT order_id FROM orders", "role": "manager"}'
# 403：{"code": "role_not_allowed"}
```

经理查全部订单，包括 `amount`：

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Authorization: Bearer $JANUS_TOKEN_MANAGER" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id, amount FROM orders ORDER BY order_id"}'
# 200：6 条订单，金额可见
```

经理指定 `analyst` 角色，结果与分析师一致：

```bash
  -d '{"sql": "SELECT order_id FROM orders", "role": "analyst"}'
# 200：订单 101、102
```

没有令牌：

```bash
curl -X POST http://127.0.0.1:8765/query -H "Content-Type: application/json" \
  -d '{"sql": "SELECT order_id FROM orders"}'
# 401：missing or invalid bearer token
```

### 4. 查看审计

```
ok     token=svc_analyst_app role=analyst sql='SELECT order_id FROM orders ...'
error  token=svc_analyst_app role=analyst sql='SELECT order_id, amount FROM orders ...'
ok     token=svc_analyst_app role=analyst sql='SELECT order_id FROM orders ...'
denied token=svc_analyst_app code=override_not_allowed sql='...'
denied token=svc_analyst_app code=role_not_allowed sql='...'
ok     token=svc_bi_console role=manager sql='SELECT order_id, amount FROM orders ...'
ok     token=svc_bi_console role=analyst sql='SELECT order_id FROM orders ...'
```

被拒绝的调用也写入审计，标记为 `denied` 并附错误码。

## 五、数据与规则如何配合

1. 分析师的会话属性为 `session_customer=1`、`session_level=1`。规划时行规则展开为 `WHERE customer_id = 1 OR 1 >= 3`，结果为 101、102。
2. 同一查询加上 `amount` 时，列规则检查 `1 >= 2`，不满足，整条查询失败。
3. 经理的 `session_level=3`，行规则为 `OR 3 >= 3`，恒真，返回全部 6 行；列规则 `3 >= 2` 也满足。

## 六、运维操作

| 需求 | 操作 | 结果 |
|---|---|---|
| 让分析师看到 `amount` | 把 `analyst` 的 `session_level` 改为 `2`，运行 `janus access report`，然后重启服务 | 列规则 `2 >= 2` 满足 |
| 收回分析师的覆盖权限 | 把 `svc_analyst_app` 的 `may_override` 改为 `false`，重启服务 | 之后的覆盖返回 `override_forbidden` |
| 轮换令牌 | 生成新值，更新环境变量 `JANUS_TOKEN_ANALYST`，重启服务 | 配置文件不用改 |
| 新增只读角色 | 在 `roles` 中加一项，加一个 `token_env`，运行 `janus access report` | 报告中出现新角色 |

每一次修改后都先运行 `janus access report`。有错误时服务不会启动，不会带着错误配置上线。

## 七、注意

- 服务端用 `--property` 固定的值，请求无法覆盖，审计中显示为 `source: fixed`。
- 列被拒绝时整条查询失败，不返回其余列。调用方需要不查该列，或换一个有权限的角色。
- 本例只在 HTTP API 和 DuckDB 上验证过。接入真实数据仓库前，要用同样的步骤再跑一遍。

完整的可运行版本在 `core/janus/examples/access-roles/`，运行 `./run_demo.sh` 即可复现上面所有输出。

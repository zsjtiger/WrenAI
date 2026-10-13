# 连接格式

🌐 [English](./connections.md) · **简体中文**

`connection_info.json` 文件（或 `--connection-info` / `--connection-file` 参数）需要一个 `datasource` 字段，以及下文列出的连接器专属字段。

## 支持的格式

**扁平格式** — 所有字段位于顶层：

```json
{
  "datasource": "postgres",
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "secret"
}
```

**包装格式（envelope）** — 连接器字段嵌套在 `properties` 之下（由 MCP 服务器和 Janus web 使用）：

```json
{
  "datasource": "postgres",
  "properties": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "postgres",
    "password": "secret"
  }
}
```

两种格式均可接受。CLI 会自动展开包装格式。

---

## 各连接器字段

## MySQL

```json
{
  "datasource": "mysql",
  "host": "localhost",
  "port": 3306,
  "database": "mydb",
  "user": "root",
  "password": "secret"
}
```

## PostgreSQL

```json
{
  "datasource": "postgres",
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "secret"
}
```

## BigQuery

```json
{
  "datasource": "bigquery",
  "project_id": "my-gcp-project",
  "dataset_id": "my_dataset",
  "credentials": "<base64-encoded-service-account-json>"
}
```

`credentials` 为可选项：若省略，连接器会回退到应用默认凭据（Application Default Credentials，即 `gcloud auth application-default login`、workload identity，或 GCE/Cloud Run 元数据服务器）。通过 `gcloud auth application-default login` 获取的 ADC 不包含 Drive 作用域；基于 Drive/Sheets 的 BigQuery 外部表仍然需要服务账号。

## Snowflake

```json
{
  "datasource": "snowflake",
  "user": "myuser",
  "password": "secret",
  "account": "myorg-myaccount",
  "database": "MYDB",
  "schema": "PUBLIC"
}
```

## Redshift（标准）

```json
{
  "datasource": "redshift",
  "host": "my-cluster.xxxx.us-east-1.redshift.amazonaws.com",
  "port": 5439,
  "database": "dev",
  "user": "awsuser",
  "password": "secret"
}
```

## Redshift（IAM）

```json
{
  "datasource": "redshift",
  "redshift_type": "redshift_iam",
  "cluster_identifier": "my-cluster",
  "database": "dev",
  "user": "awsuser",
  "region": "us-east-1",
  "access_key_id": "AKIA...",
  "access_key_secret": "secret"
}
```

## DuckDB（本地文件）

```json
{
  "datasource": "duckdb",
  "url": "/path/to/data",
  "format": "parquet"
}
```

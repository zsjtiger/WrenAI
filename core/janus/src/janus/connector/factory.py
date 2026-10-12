import importlib

from janus.mdl.cte_rewriter import get_sqlglot_dialect
from janus.model.data_source import DataSource
from janus.model.error import ErrorCode, JanusError

_REGISTRY: dict[DataSource, str] = {
    DataSource.postgres: "janus.connector.postgres",
    DataSource.mysql: "janus.connector.mysql",
    DataSource.doris: "janus.connector.mysql",
    DataSource.mssql: "janus.connector.mssql",
    DataSource.canner: "janus.connector.canner",
    DataSource.bigquery: "janus.connector.bigquery",
    DataSource.datafusion: "janus.connector.datafusion",
    DataSource.local_file: "janus.connector.duckdb",
    DataSource.s3_file: "janus.connector.duckdb",
    DataSource.minio_file: "janus.connector.duckdb",
    DataSource.gcs_file: "janus.connector.duckdb",
    DataSource.duckdb: "janus.connector.duckdb",
    DataSource.redshift: "janus.connector.redshift",
    DataSource.spark: "janus.connector.spark",
    DataSource.databricks: "janus.connector.databricks",
    DataSource.trino: "janus.connector.trino",
    DataSource.clickhouse: "janus.connector.clickhouse",
    DataSource.oracle: "janus.connector.oracle",
    DataSource.snowflake: "janus.connector.snowflake",
    DataSource.athena: "janus.connector.athena",
}

# Map data sources to the correct pip extra when they share a connector module
_INSTALL_EXTRA: dict[DataSource, str] = {
    DataSource.doris: "mysql",
    DataSource.canner: "postgres",
    DataSource.local_file: "duckdb",
    DataSource.s3_file: "duckdb",
    DataSource.minio_file: "duckdb",
    DataSource.gcs_file: "duckdb",
}

_NEEDS_DATA_SOURCE = {
    DataSource.mysql,
    DataSource.doris,
    DataSource.trino,
}


def get_connector(data_source: DataSource, connection_info):
    module_path = _REGISTRY.get(data_source)
    if module_path is None:
        raise JanusError(
            ErrorCode.NOT_IMPLEMENTED,
            f"Unsupported data source: {data_source}",
        )

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        extra = _INSTALL_EXTRA.get(data_source, data_source.value)
        raise JanusError(
            ErrorCode.NOT_IMPLEMENTED,
            f"Connector '{data_source.value}' requires additional dependencies: {e}. "
            f"Install with: pip install 'janusai[{extra}]'",
        ) from e

    if data_source in _NEEDS_DATA_SOURCE:
        connector = module.create_connector(data_source, connection_info)
    else:
        connector = module.create_connector(connection_info)

    # Which lexical forms exist is a per-dialect property (`\'` is an escape in
    # MySQL/BigQuery but not in standard SQL), and the DataSource is only known
    # here -- so the strip helpers get the dialect from the factory rather than
    # hard-coding it per connector.
    connector.dialect = get_sqlglot_dialect(data_source)
    return connector

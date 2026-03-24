import duckdb
import threading
from config import settings
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Thread-local DuckDB connections
#
# DuckDB in-memory connections are NOT thread-safe when shared.
# Each thread gets its own private connection loaded with the
# same CSV data, eliminating all concurrent-access segfaults.
# ─────────────────────────────────────────────────────────────
_thread_local = threading.local()


def _load_csv(conn: duckdb.DuckDBPyConnection) -> None:
    data_dir = settings.DATA_DIR
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    for csv_file in csv_files:
        table_name = csv_file.replace(".csv", "")
        file_path = os.path.join(data_dir, csv_file)
        conn.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}')"
        )
        logger.info(f"Loaded {csv_file} into table {table_name}")


def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Return a DuckDB connection that is private to the calling thread.
    Creates and initialises it on first access per thread.
    """
    if not hasattr(_thread_local, "connection") or _thread_local.connection is None:
        conn = duckdb.connect(database=":memory:", read_only=False)
        _load_csv(conn)
        _thread_local.connection = conn
        logger.debug(f"Created new thread-local DuckDB connection for thread {threading.current_thread().name}")
    return _thread_local.connection


def get_schema_snapshot() -> Dict[str, Any]:
    conn = get_connection()
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    schema_snapshot = {}
    for table in tables:
        table_name = table[0]
        columns = conn.execute(
            f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'"
        ).fetchall()
        schema_snapshot[table_name] = [
            {"name": col_name, "type": col_type} for col_name, col_type in columns
        ]
    return schema_snapshot


def get_schema_as_json() -> str:
    return json.dumps(get_schema_snapshot(), indent=2)


def get_sample_rows(table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    return get_connection().execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()


def execute_query(sql_query: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        result = conn.execute(sql_query)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise QueryExecutionError(str(e), sql_query)


class QueryExecutionError(Exception):
    def __init__(self, message: str, query: str):
        self.message = message
        self.query = query
        super().__init__(f"SQL Error: {message}\nQuery: {query}")
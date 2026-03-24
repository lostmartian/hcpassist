import re
import sqlparse
import logging
from typing import Optional
from db.connector import get_connection

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "MERGE", "REPLACE", "CALL",
}

reg_pattern = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE
)

def validate_sql_query(sql_query: str) -> str:
    if not sql_query or not sql_query.strip():
        logger.error(f"Invalid SQL query: {sql_query}")
        raise ValueError("SQL query cannot be empty.")
    
    parsed_query = sqlparse.parse(sql_query)
    if not parsed_query:
        logger.error(f"Invalid SQL query: {sql_query}")
        raise ValueError("Invalid SQL query.")

    for stmt in parsed_query:
        if stmt.get_type() not in ["SELECT", None]:
            logger.error(f"Forbidden query type: {stmt.get_type()}")
            raise ValueError("Only SELECT queries are allowed.")

    for match in reg_pattern.finditer(sql_query):
        before = sql_query[:match.start()]
        after = sql_query[match.end():]
        single_quote = before.count("'" )
        double_quote = before.count('"')
        if single_quote % 2 == 0 and double_quote % 2 == 0:
            logger.error(f"Forbidden keyword found: {match.group(1)}")
            raise ValueError(f"Forbidden keyword found: {match.group(1)}")
    if not is_sql_valid(sql_query):
        logger.error(f"Invalid SQL query: {sql_query}")
        raise ValueError("Invalid SQL query.")
    return sql_query

def is_sql_valid(sql: str) -> bool:
    conn = get_connection()
    try:
        conn.execute(f"PREPARE check_query AS {sql}")
        conn.execute("DEALLOCATE check_query")
        return True
    except Exception as e:
        logger.error(f"SQL Schema Validation failed: {e}")
        return False
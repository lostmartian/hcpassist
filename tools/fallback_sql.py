from langchain_core.tools import tool
from db.connector import execute_query, get_schema_snapshot
from db.validator import validate_sql_query

@tool
def execute_safe_sql(sql_query: str) -> str:
    """Execute a raw SQL query against the DuckDB database with safety checks.

    This is a FALLBACK tool - use it only when the pre-defined tools cannot answer the question.

    Pre-defined tools available:
    - get_hcp_rx_performance, get_rep_activity_summary, get_account_payor_mix,
      get_market_share_metrics, get_territory_summary, get_hcp_profile,
      get_account_profile, get_date_info, get_hcp_ranking, get_rx_trend,
      compare_rx_performance, get_rep_performance, get_specialty_analysis,
      get_rep_hcp_coverage, get_account_performance, get_kpi_dashboard,
      get_growth_analysis

    The query MUST be a SELECT statement. Any DDL/DML (DROP, DELETE, INSERT, etc.)
    will be rejected.

    Available tables: fact_rx, fact_rep_activity, fact_payor_mix, fact_ln_metrics,
    hcp_dim, rep_dim, account_dim, territory_dim, date_dim.

    Key join notes:
    - date_id is an integer in YYYYMMDD format; join to date_dim for temporal queries
    - rep_dim.region is a string name ('Territory 1'), not territory_id
    - fact_ln_metrics.entity_id is polymorphic: entity_type='H' → hcp_dim.hcp_id, entity_type='A' → account_dim.account_id

    Args:
        sql_query: A valid SELECT SQL query string.
    """
    try:
        validated_sql = validate_sql_query(sql_query)
    except Exception as e:
        return f"SAFETY ERROR: {str(e)}"

    try:
        results = execute_query(validated_sql)
        if not results:
            return "Query returned no results."
        return str(results)
    except Exception as e:
        return f"EXECUTION ERROR: {str(e)}"
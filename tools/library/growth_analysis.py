"""Growth Analysis Tool.

Period-over-period growth calculation for Rx volume, patient counts, or market share.
Identifies growth and decline trends across entities.
Join paths: fact_rx → date_dim → hcp_dim, fact_ln_metrics
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_growth_analysis(
    metric: str = "trx",
    group_by: str = "territory",
    period1_quarter: Optional[str] = None,
    period1_year: Optional[int] = None,
    period2_quarter: Optional[str] = None,
    period2_year: Optional[int] = None,
    territory: Optional[str] = None,
    specialty: Optional[str] = None,
) -> str:
    """Calculate period-over-period growth for key metrics.

    Compares two time periods and shows the absolute and percentage change.
    If period params are not specified, defaults to comparing the two most recent quarters.

    Example: "TRx growth from Q4 2024 to Q1 2025" →
        get_growth_analysis(metric="trx", period1_quarter="Q4", period1_year=2024,
                            period2_quarter="Q1", period2_year=2025)
    Example: "Which territory grew the most?" → get_growth_analysis(group_by="territory")

    Args:
        metric: Growth metric — 'trx', 'nrx', 'market_share', or 'patient_count'. Default: 'trx'.
        group_by: Grouping — 'territory', 'hcp', 'specialty', or 'overall'. Default: 'territory'.
        period1_quarter: Earlier period quarter (e.g., 'Q4'). Optional.
        period1_year: Earlier period year (e.g., 2024). Optional.
        period2_quarter: Later period quarter (e.g., 'Q1'). Optional.
        period2_year: Later period year (e.g., 2025). Optional.
        territory: Filter by territory. Optional.
        specialty: Filter by specialty. Optional.
    """
    if metric in ("trx", "nrx"):
        metric_col = "rx.trx_cnt" if metric == "trx" else "rx.nrx_cnt"

        if group_by == "territory":
            group_col = "t.name"
            group_alias = "entity_name"
        elif group_by == "hcp":
            group_col = "h.full_name"
            group_alias = "entity_name"
        elif group_by == "specialty":
            group_col = "h.specialty"
            group_alias = "entity_name"
        elif group_by == "overall":
            group_col = "'Overall'"
            group_alias = "entity_name"
        else:
            return f"Invalid group_by: '{group_by}'. Must be 'territory', 'hcp', 'specialty', or 'overall'."

        # Build period filters
        p1_filter = ""
        p2_filter = ""
        if period1_quarter and period1_year:
            p1_filter = f"d.quarter = '{period1_quarter}' AND d.year = {period1_year}"
        if period2_quarter and period2_year:
            p2_filter = f"d.quarter = '{period2_quarter}' AND d.year = {period2_year}"

        # If no periods specified, auto-detect two most recent quarters
        if not p1_filter or not p2_filter:
            auto_sql = """
            SELECT DISTINCT d.year, d.quarter
            FROM date_dim d
            JOIN fact_rx rx ON d.date_id = rx.date_id
            ORDER BY d.year DESC, d.quarter DESC
            LIMIT 2
            """
            try:
                periods = execute_query(auto_sql)
                if len(periods) < 2:
                    return "Not enough data periods to compute growth. Need at least 2 quarters."
                if not p2_filter:
                    p2_filter = f"d.quarter = '{periods[0]['quarter']}' AND d.year = {periods[0]['year']}"
                if not p1_filter:
                    p1_filter = f"d.quarter = '{periods[1]['quarter']}' AND d.year = {periods[1]['year']}"
            except Exception as e:
                return f"Error detecting periods: {str(e)}"

        base_where = f"d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'"
        extra = ""
        if territory:
            extra += f" AND t.name ILIKE '%{territory}%'"
        if specialty:
            extra += f" AND h.specialty ILIKE '%{specialty}%'"

        sql = f"""
        WITH period1 AS (
            SELECT {group_col} AS {group_alias}, SUM({metric_col}) AS val
            FROM fact_rx rx
            JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
            JOIN territory_dim t ON h.territory_id = t.territory_id
            JOIN date_dim d ON rx.date_id = d.date_id
            WHERE {base_where} AND {p1_filter}{extra}
            GROUP BY {group_col}
        ),
        period2 AS (
            SELECT {group_col} AS {group_alias}, SUM({metric_col}) AS val
            FROM fact_rx rx
            JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
            JOIN territory_dim t ON h.territory_id = t.territory_id
            JOIN date_dim d ON rx.date_id = d.date_id
            WHERE {base_where} AND {p2_filter}{extra}
            GROUP BY {group_col}
        )
        SELECT
            COALESCE(p1.{group_alias}, p2.{group_alias}) AS {group_alias},
            COALESCE(p1.val, 0) AS period1_value,
            COALESCE(p2.val, 0) AS period2_value,
            COALESCE(p2.val, 0) - COALESCE(p1.val, 0) AS absolute_change,
            CASE
                WHEN COALESCE(p1.val, 0) = 0 THEN NULL
                ELSE ROUND(100.0 * (COALESCE(p2.val, 0) - p1.val) / p1.val, 1)
            END AS growth_pct
        FROM period1 p1
        FULL OUTER JOIN period2 p2 ON p1.{group_alias} = p2.{group_alias}
        ORDER BY growth_pct DESC NULLS LAST
        LIMIT 50
        """

    elif metric in ("market_share", "patient_count"):
        val_col = "m.est_market_share" if metric == "market_share" else "m.ln_patient_cnt"
        agg = "AVG" if metric == "market_share" else "SUM"

        # For market share, compare quarter_ids
        if not period1_quarter or not period1_year or not period2_quarter or not period2_year:
            auto_sql = """
            SELECT DISTINCT quarter_id
            FROM fact_ln_metrics
            ORDER BY quarter_id DESC
            LIMIT 2
            """
            try:
                periods = execute_query(auto_sql)
                if len(periods) < 2:
                    return "Not enough data periods for growth analysis."
                q2 = periods[0]["quarter_id"]
                q1 = periods[1]["quarter_id"]
            except Exception as e:
                return f"Error detecting periods: {str(e)}"
        else:
            q1 = f"{period1_year}{period1_quarter}"
            q2 = f"{period2_year}{period2_quarter}"

        sql = f"""
        WITH period1 AS (
            SELECT h.full_name AS entity_name, {agg}({val_col}) AS val
            FROM fact_ln_metrics m
            JOIN hcp_dim h ON m.entity_id = h.hcp_id
            WHERE m.entity_type = 'H' AND m.quarter_id = '{q1}'
            GROUP BY h.full_name
        ),
        period2 AS (
            SELECT h.full_name AS entity_name, {agg}({val_col}) AS val
            FROM fact_ln_metrics m
            JOIN hcp_dim h ON m.entity_id = h.hcp_id
            WHERE m.entity_type = 'H' AND m.quarter_id = '{q2}'
            GROUP BY h.full_name
        )
        SELECT
            COALESCE(p1.entity_name, p2.entity_name) AS entity_name,
            COALESCE(p1.val, 0) AS period1_value,
            COALESCE(p2.val, 0) AS period2_value,
            ROUND(COALESCE(p2.val, 0) - COALESCE(p1.val, 0), 2) AS absolute_change,
            CASE
                WHEN COALESCE(p1.val, 0) = 0 THEN NULL
                ELSE ROUND(100.0 * (COALESCE(p2.val, 0) - p1.val) / p1.val, 1)
            END AS growth_pct
        FROM period1 p1
        FULL OUTER JOIN period2 p2 ON p1.entity_name = p2.entity_name
        ORDER BY growth_pct DESC NULLS LAST
        LIMIT 50
        """
    else:
        return f"Invalid metric: '{metric}'. Must be 'trx', 'nrx', 'market_share', or 'patient_count'."

    try:
        results = execute_query(sql)
        if not results:
            return "No growth data found for the specified parameters."
        return str(results)
    except Exception as e:
        return f"Error computing growth analysis: {str(e)}"

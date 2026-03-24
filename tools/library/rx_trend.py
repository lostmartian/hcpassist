"""Prescription Trend Tool.

Show Rx volume trends over time (monthly or quarterly).
Join path: fact_rx → hcp_dim → territory_dim → date_dim
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_rx_trend(
    granularity: str = "monthly",
    hcp_name: Optional[str] = None,
    territory: Optional[str] = None,
    specialty: Optional[str] = None,
    brand: str = "GAZYVA",
    metric: str = "trx",
    year: Optional[int] = None,
) -> str:
    """Get prescription volume trends over time (monthly or quarterly).

    Use for questions about how prescriptions change over time, growth patterns,
    or seasonal trends.

    Example: "Show me the monthly TRx trend" → get_rx_trend(granularity="monthly")
    Example: "Quarterly NRx trend for Dr. Garcia" →
        get_rx_trend(granularity="quarterly", hcp_name="Garcia", metric="nrx")

    Args:
        granularity: Time grouping — 'monthly' or 'quarterly'. Default: 'monthly'.
        hcp_name: Filter by HCP name. Optional.
        territory: Filter by territory name. Optional.
        specialty: Filter by HCP specialty. Optional.
        brand: Pharmaceutical brand. Default: 'GAZYVA'.
        metric: 'trx' for total or 'nrx' for new prescriptions. Default: 'trx'.
        year: Filter by specific year. Optional.
    """
    metric_col = "rx.trx_cnt" if metric.lower() == "trx" else "rx.nrx_cnt"

    if granularity == "monthly":
        time_cols = "d.year, MONTH(d.calendar_date) AS month_num"
        group_cols = "d.year, month_num"
        order_cols = "d.year, month_num"
    elif granularity == "quarterly":
        time_cols = "d.year, d.quarter"
        group_cols = "d.year, d.quarter"
        order_cols = "d.year, d.quarter"
    else:
        return f"Invalid granularity: '{granularity}'. Must be 'monthly' or 'quarterly'."

    sql = f"""
    SELECT
        {time_cols},
        SUM({metric_col}) AS total_{metric.lower()},
        COUNT(DISTINCT rx.hcp_id) AS hcp_count
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if hcp_name:
        clean_name = hcp_name.replace(".", "").replace(",", "").strip()
        fuzzy_name = "%".join(clean_name.split())
        sql += f" AND h.full_name ILIKE '%{fuzzy_name}%'"
    if territory:
        sql += f" AND t.name ILIKE '%{territory}%'"
    if specialty:
        sql += f" AND h.specialty ILIKE '%{specialty}%'"
    if brand:
        sql += f" AND rx.brand_code = '{brand}'"
    if year:
        sql += f" AND d.year = {year}"

    sql += f" GROUP BY {group_cols} ORDER BY {order_cols}"

    try:
        results = execute_query(sql)
        if not results:
            return f"No trend data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error computing Rx trend: {str(e)}"

"""Territory Summary Tool.

Pre-defined SQL function for cross-metric aggregation at the territory level.
Join path: Aggregates over hcp_dim, fact_rx, fact_rep_activity filtered through territory_dim.
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_territory_summary(
    territory: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get a summary of key metrics aggregated at the territory level.

    Includes prescription volume, rep activity counts, and HCP counts per territory.

    Args:
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
        year: Filter by year (2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
    """
    # Prescription summary by territory
    rx_sql = f"""
    SELECT
        t.name AS territory_name,
        t.geo_type,
        COUNT(DISTINCT h.hcp_id) AS hcp_count,
        SUM(rx.trx_cnt) AS total_trx,
        SUM(rx.nrx_cnt) AS total_nrx
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """
    if territory:
        rx_sql += f" AND t.name ILIKE '%{territory}%'"
    if year:
        rx_sql += f" AND d.year = {year}"
    if quarter:
        rx_sql += f" AND d.quarter = '{quarter}'"
    rx_sql += " GROUP BY t.name, t.geo_type ORDER BY total_trx DESC"

    # Activity summary by territory
    act_sql = f"""
    SELECT
        r.region AS territory_name,
        COUNT(*) AS total_activities,
        SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed_activities,
        SUM(CASE WHEN a.activity_type = 'call' THEN 1 ELSE 0 END) AS total_calls,
        SUM(CASE WHEN a.activity_type = 'lunch_meeting' THEN 1 ELSE 0 END) AS total_meetings
    FROM fact_rep_activity a
    JOIN rep_dim r ON a.rep_id = r.rep_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """
    if territory:
        act_sql += f" AND r.region ILIKE '%{territory}%'"
    if year:
        act_sql += f" AND d.year = {year}"
    if quarter:
        act_sql += f" AND d.quarter = '{quarter}'"
    act_sql += " GROUP BY r.region ORDER BY total_activities DESC"

    try:
        rx_results = execute_query(rx_sql)
        act_results = execute_query(act_sql)

        output = {"prescription_summary": rx_results, "activity_summary": act_results}
        if not rx_results and not act_results:
            return "No territory data found for the specified filters."
        return str(output)
    except Exception as e:
        return f"Error executing territory summary: {str(e)}"

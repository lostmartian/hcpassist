"""Rep Performance / KPI Tool.

Calculate detailed rep performance KPIs: activity volume, completion rate,
call-to-meeting ratio, avg duration.
Join path: fact_rep_activity → rep_dim → date_dim
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_rep_performance(
    rep_name: Optional[str] = None,
    territory: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get detailed performance KPIs for sales representatives.

    Returns: total activities, calls, meetings, completion rate,
    cancellation rate, average duration, and unique HCPs/accounts covered.

    Example: "How efficient is Morgan Chen?" → get_rep_performance(rep_name="Morgan Chen")
    Example: "Rep performance for Territory 1 in Q1 2025" →
        get_rep_performance(territory="Territory 1", quarter="Q1", year=2025)

    Args:
        rep_name: Filter by rep name. Optional.
        territory: Filter by territory/region. Optional.
        year: Filter by year. Optional.
        quarter: Filter by quarter. Optional.
    """
    sql = f"""
    SELECT
        r.first_name || ' ' || r.last_name AS rep_name,
        r.region AS territory_name,
        COUNT(*) AS total_activities,
        SUM(CASE WHEN a.activity_type = 'call' THEN 1 ELSE 0 END) AS total_calls,
        SUM(CASE WHEN a.activity_type = 'lunch_meeting' THEN 1 ELSE 0 END) AS total_meetings,
        SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed,
        SUM(CASE WHEN a.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
        SUM(CASE WHEN a.status = 'scheduled' THEN 1 ELSE 0 END) AS scheduled,
        ROUND(100.0 * SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_rate_pct,
        ROUND(AVG(a.duration_min), 1) AS avg_duration_min,
        COUNT(DISTINCT a.hcp_id) AS unique_hcps_visited,
        COUNT(DISTINCT a.account_id) AS unique_accounts_visited
    FROM fact_rep_activity a
    JOIN rep_dim r ON a.rep_id = r.rep_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if rep_name:
        clean_rep = rep_name.replace(".", "").replace(",", "").strip()
        fuzzy_rep = "%".join(clean_rep.split())
        sql += f" AND (r.first_name || ' ' || r.last_name) ILIKE '%{fuzzy_rep}%'"
    if territory:
        sql += f" AND r.region ILIKE '%{territory}%'"
    if year:
        sql += f" AND d.year = {year}"
    if quarter:
        sql += f" AND d.quarter = '{quarter}'"

    sql += " GROUP BY rep_name, r.region ORDER BY total_activities DESC LIMIT 50"

    try:
        results = execute_query(sql)
        if not results:
            return "No rep performance data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error computing rep performance: {str(e)}"

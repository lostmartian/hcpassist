"""Rep Activity Summary Tool.

Pre-defined SQL function for querying sales rep activity data.
Join path: fact_rep_activity → rep_dim (rep_id) → hcp_dim (hcp_id) → account_dim (account_id) → date_dim (date_id)

KEY GOTCHA: rep_dim.region is a STRING name ('Territory 1'), NOT the integer territory_id.
            Join to territory_dim.name for territory-based filtering.
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query
from config import settings


@tool
def get_rep_activity_summary(
    rep_name: Optional[str] = None,
    territory: Optional[str] = None,
    activity_type: Optional[str] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get sales representative activity summary with details on calls, meetings, and outcomes.

    Args:
        rep_name: Filter by rep first or last name (e.g., 'Taylor' or 'Kim'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
        activity_type: Filter by activity type ('call' or 'lunch_meeting'). Optional.
        status: Filter by activity status ('completed', 'scheduled', 'cancelled'). Optional.
        year: Filter by year (2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
    """
    sql = f"""
    SELECT
        r.first_name || ' ' || r.last_name AS rep_name,
        r.region AS territory_name,
        a.activity_type,
        a.status,
        COUNT(*) AS activity_count,
        AVG(a.duration_min) AS avg_duration_min,
        h.full_name AS hcp_name,
        acc.name AS account_name
    FROM fact_rep_activity a
    JOIN rep_dim r ON a.rep_id = r.rep_id
    JOIN hcp_dim h ON a.hcp_id = h.hcp_id
    JOIN account_dim acc ON a.account_id = acc.account_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if rep_name:
        clean_rep = rep_name.replace(".", "").replace(",", "").strip()
        fuzzy_rep = "%".join(clean_rep.split())
        sql += f" AND (r.first_name || ' ' || r.last_name) ILIKE '%{fuzzy_rep}%'"
    if territory:
        # KEY: rep_dim.region is a string name, NOT territory_id
        sql += f" AND r.region ILIKE '%{territory}%'"
    if activity_type:
        sql += f" AND a.activity_type = '{activity_type}'"
    if status:
        sql += f" AND a.status = '{status}'"
    if year:
        sql += f" AND d.year = {year}"
    if quarter:
        sql += f" AND d.quarter = '{quarter}'"

    sql += """
    GROUP BY rep_name, r.region, a.activity_type, a.status, h.full_name, acc.name
    ORDER BY activity_count DESC
    LIMIT 50
    """

    try:
        results = execute_query(sql)
        if not results:
            return "No activity data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error executing query: {str(e)}"

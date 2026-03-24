"""Rep Activity Summary Tool.

Pre-defined SQL function for querying sales rep activity data.
Join path: fact_rep_activity → rep_dim (rep_id) → hcp_dim (hcp_id) → account_dim (account_id) → date_dim (date_id)

KEY GOTCHA: rep_dim.region is a STRING name ('Territory 1'), NOT the integer territory_id.
            Join to territory_dim.name for territory-based filtering.

FIX (v2): When no hcp_name is specified, return TOTAL counts aggregated at rep+type+status level
          (no LIMIT truncation). When hcp_name IS specified, return per-HCP/account detail.
          This prevents the LLM from summing partial LIMIT-50 rows and getting wrong totals.
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
    hcp_name: Optional[str] = None,
    aggregate: bool = True,
) -> str:
    """Get sales representative activity summary with details on calls, meetings, and outcomes.

    By default (aggregate=True) returns TOTAL counts per rep — use this for questions like
    'how many total activities / calls / lunch meetings / cancellations does rep X have'.

    Set aggregate=False to get a per-HCP / per-account breakdown (use for engagement detail).

    Args:
        rep_name: Filter by rep full name or partial name (e.g., 'Taylor Kim'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
        activity_type: Filter by activity type ('call' or 'lunch_meeting'). Optional.
        status: Filter by activity status ('completed', 'scheduled', 'cancelled'). Optional.
        year: Filter by year (2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
        hcp_name: Filter by HCP full name (for per-HCP detail). Optional.
        aggregate: If True (default), return per-rep total counts. If False, return per-HCP/account detail.
    """

    base_joins = f"""
    FROM fact_rep_activity a
    JOIN rep_dim r ON a.rep_id = r.rep_id
    JOIN hcp_dim h ON a.hcp_id = h.hcp_id
    JOIN account_dim acc ON a.account_id = acc.account_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    filters = ""
    if rep_name:
        clean_rep = rep_name.replace(".", "").replace(",", "").strip()
        fuzzy_rep = "%".join(clean_rep.split())
        filters += f" AND (r.first_name || ' ' || r.last_name) ILIKE '%{fuzzy_rep}%'"
    if territory:
        filters += f" AND r.region ILIKE '%{territory}%'"
    if activity_type:
        filters += f" AND a.activity_type = '{activity_type}'"
    if status:
        filters += f" AND a.status = '{status}'"
    if year:
        filters += f" AND d.year = {year}"
    if quarter:
        filters += f" AND d.quarter = '{quarter}'"
    if hcp_name:
        clean_hcp = hcp_name.replace(".", "").replace(",", "").strip()
        fuzzy_hcp = "%".join(clean_hcp.split())
        filters += f" AND h.full_name ILIKE '%{fuzzy_hcp}%'"

    if aggregate and not hcp_name:
        # ── AGGREGATE MODE: one row per rep+activity_type+status with TOTAL count ──
        # No LIMIT — these are already grouped totals, not exploded rows.
        sql = f"""
        SELECT
            r.first_name || ' ' || r.last_name AS rep_name,
            r.region AS territory_name,
            a.activity_type,
            a.status,
            COUNT(*) AS total_activity_count,
            AVG(a.duration_min) AS avg_duration_min
        {base_joins}
        {filters}
        GROUP BY rep_name, r.region, a.activity_type, a.status
        ORDER BY rep_name, a.activity_type, a.status
        """
    else:
        # ── DETAIL MODE: per-HCP/account breakdown (use for engagement analysis) ──
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
        {base_joins}
        {filters}
        GROUP BY rep_name, r.region, a.activity_type, a.status, h.full_name, acc.name
        ORDER BY activity_count DESC
        LIMIT 100
        """

    try:
        results = execute_query(sql)
        if not results:
            return "No activity data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error executing query: {str(e)}"

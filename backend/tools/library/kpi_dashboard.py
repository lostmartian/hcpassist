"""Executive KPI Dashboard Tool.

One-call aggregate of all key performance indicators across the entire dataset.
Touches: fact_rx, fact_rep_activity, fact_ln_metrics, hcp_dim, rep_dim, territory_dim, date_dim
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query
from config import settings


@tool
def get_kpi_dashboard(
    territory: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get an executive-level KPI dashboard with key metrics across all data.

    Returns: total TRx/NRx, top HCP, top territory, rep utilization,
    average market share, and activity completion rate — all in one call.

    Ideal for questions like "Give me an overview" or "Executive summary for Q1 2025."

    Args:
        territory: Filter all KPIs to a specific territory. Optional.
        year: Filter by year. Optional.
        quarter: Filter by quarter. Optional.
    """
    date_filter = f"d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'"
    extra_filters = ""
    if year:
        extra_filters += f" AND d.year = {year}"
    if quarter:
        extra_filters += f" AND d.quarter = '{quarter}'"

    # KPI 1: Rx summary
    rx_sql = f"""
    SELECT
        SUM(rx.trx_cnt) AS total_trx,
        SUM(rx.nrx_cnt) AS total_nrx,
        COUNT(DISTINCT rx.hcp_id) AS prescribing_hcps,
        ROUND(AVG(rx.trx_cnt), 2) AS avg_trx_per_record
    FROM fact_rx rx
    JOIN date_dim d ON rx.date_id = d.date_id
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    WHERE {date_filter}{extra_filters}
    """
    if territory:
        rx_sql += f" AND t.name ILIKE '%{territory}%'"

    # KPI 2: Top prescriber
    top_hcp_sql = f"""
    SELECT
        h.full_name AS top_hcp,
        SUM(rx.trx_cnt) AS hcp_trx
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE {date_filter}{extra_filters}
    """
    if territory:
        top_hcp_sql += f" AND t.name ILIKE '%{territory}%'"
    top_hcp_sql += " GROUP BY h.full_name ORDER BY hcp_trx DESC LIMIT 1"

    # KPI 3: Territory breakdown
    terr_sql = f"""
    SELECT
        t.name AS territory_name,
        SUM(rx.trx_cnt) AS territory_trx
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE {date_filter}{extra_filters}
    """
    if territory:
        terr_sql += f" AND t.name ILIKE '%{territory}%'"
    terr_sql += " GROUP BY t.name ORDER BY territory_trx DESC"

    # KPI 4: Rep activity summary
    rep_sql = f"""
    SELECT
        COUNT(*) AS total_activities,
        SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed,
        ROUND(100.0 * SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_rate_pct,
        COUNT(DISTINCT a.rep_id) AS active_reps,
        SUM(CASE WHEN a.activity_type = 'call' THEN 1 ELSE 0 END) AS total_calls,
        SUM(CASE WHEN a.activity_type = 'lunch_meeting' THEN 1 ELSE 0 END) AS total_meetings
    FROM fact_rep_activity a
    JOIN rep_dim r ON a.rep_id = r.rep_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE {date_filter}{extra_filters}
    """
    if territory:
        rep_sql += f" AND r.region ILIKE '%{territory}%'"

    # KPI 5: Market share overview
    ms_sql = """
    SELECT
        ROUND(AVG(m.est_market_share), 2) AS avg_market_share,
        SUM(m.ln_patient_cnt) AS total_patients,
        COUNT(DISTINCT m.entity_id) AS entities_tracked
    FROM fact_ln_metrics m
    """

    try:
        rx_kpi = execute_query(rx_sql)
        top_hcp = execute_query(top_hcp_sql)
        terr_kpi = execute_query(terr_sql)
        rep_kpi = execute_query(rep_sql)
        ms_kpi = execute_query(ms_sql)

        dashboard = {
            "rx_summary": rx_kpi[0] if rx_kpi else {},
            "top_prescriber": top_hcp[0] if top_hcp else {},
            "territory_breakdown": terr_kpi,
            "rep_activity_summary": rep_kpi[0] if rep_kpi else {},
            "market_share_overview": ms_kpi[0] if ms_kpi else {},
        }
        return str(dashboard)
    except Exception as e:
        return f"Error building KPI dashboard: {str(e)}"

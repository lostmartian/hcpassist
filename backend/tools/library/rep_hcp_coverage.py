"""Rep-to-HCP Coverage & Engagement Tool.

Analyze which HCPs a rep has visited, how often, and their Rx output.
Multi-table join: fact_rep_activity → rep_dim, hcp_dim → fact_rx → date_dim
Identifies low-coverage high-value targets.
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query
from config import settings


@tool
def get_rep_hcp_coverage(
    rep_name: Optional[str] = None,
    territory: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
    show_uncovered: bool = False,
) -> str:
    """Analyze rep-to-HCP engagement and coverage.

    Shows which HCPs a rep has visited, visit count, and those HCPs' prescription volume.
    Optionally identifies "uncovered" high-value HCPs (those with Rx but no rep visits).

    Example: "Which HCPs has Morgan Chen visited?" → get_rep_hcp_coverage(rep_name="Morgan Chen")
    Example: "Show uncovered HCPs in Territory 1" →
        get_rep_hcp_coverage(territory="Territory 1", show_uncovered=True)

    Args:
        rep_name: Filter by rep name. Optional.
        territory: Filter by territory/region. Optional.
        year: Filter by year. Optional.
        quarter: Filter by quarter. Optional.
        show_uncovered: If True, shows HCPs with Rx but NO rep visits. Default: False.
    """
    if show_uncovered:
        # Find HCPs with Rx activity but zero rep visits
        sql = f"""
        SELECT
            h.full_name AS hcp_name,
            h.specialty,
            h.tier,
            t.name AS territory_name,
            SUM(rx.trx_cnt) AS total_trx,
            SUM(rx.nrx_cnt) AS total_nrx
        FROM fact_rx rx
        JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        JOIN date_dim d ON rx.date_id = d.date_id
        WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
          AND h.hcp_id NOT IN (
              SELECT DISTINCT a.hcp_id
              FROM fact_rep_activity a
              JOIN date_dim d2 ON a.date_id = d2.date_id
              WHERE d2.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
        """
        if year:
            sql += f" AND d2.year = {year}"
        if quarter:
            sql += f" AND d2.quarter = '{quarter}'"
        sql += ")"
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        if year:
            sql += f" AND d.year = {year}"
        if quarter:
            sql += f" AND d.quarter = '{quarter}'"
        sql += " GROUP BY h.full_name, h.specialty, h.tier, t.name ORDER BY total_trx DESC LIMIT 50"

    else:
        # Show rep → HCP coverage with visit counts and Rx
        sql = f"""
        SELECT
            r.first_name || ' ' || r.last_name AS rep_name,
            h.full_name AS hcp_name,
            h.specialty,
            h.tier,
            COUNT(a.activity_id) AS visit_count,
            SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed_visits,
            COALESCE(rx_data.total_trx, 0) AS hcp_total_trx
        FROM fact_rep_activity a
        JOIN rep_dim r ON a.rep_id = r.rep_id
        JOIN hcp_dim h ON a.hcp_id = h.hcp_id
        JOIN date_dim d ON a.date_id = d.date_id
        LEFT JOIN (
            SELECT rx.hcp_id, SUM(rx.trx_cnt) AS total_trx
            FROM fact_rx rx
            JOIN date_dim d ON rx.date_id = d.date_id
            WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
            GROUP BY rx.hcp_id
        ) rx_data ON h.hcp_id = rx_data.hcp_id
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
        sql += """
        GROUP BY rep_name, h.full_name, h.specialty, h.tier, rx_data.total_trx
        ORDER BY visit_count DESC
        LIMIT 50
        """

    try:
        results = execute_query(sql)
        if not results:
            label = "uncovered HCPs" if show_uncovered else "coverage data"
            return f"No {label} found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error computing rep-HCP coverage: {str(e)}"

"""Specialty Analysis Tool.

Aggregate prescription and market share metrics by HCP specialty.
Join paths: fact_rx → hcp_dim, fact_ln_metrics → hcp_dim
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query
from config import settings


@tool
def get_specialty_analysis(
    specialty: Optional[str] = None,
    territory: Optional[str] = None,
    metric: str = "trx",
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Analyze prescription volume and market share grouped by HCP specialty.

    Use for questions like "Which specialty writes the most prescriptions?"
    or "Compare Rheumatology vs Oncology market share."

    Args:
        specialty: Filter to a single specialty. Optional (returns all if not specified).
        territory: Filter by territory name. Optional.
        metric: Analysis metric — 'trx', 'nrx', or 'market_share'. Default: 'trx'.
        year: Filter by year. Optional (used for trx/nrx).
        quarter: Filter by quarter. Optional (used for trx/nrx).
    """
    if metric in ("trx", "nrx"):
        metric_col = "rx.trx_cnt" if metric == "trx" else "rx.nrx_cnt"
        sql = f"""
        SELECT
            h.specialty,
            COUNT(DISTINCT h.hcp_id) AS hcp_count,
            SUM({metric_col}) AS total_{metric},
            ROUND(AVG({metric_col}), 2) AS avg_{metric}_per_record,
            t.name AS territory_name
        FROM fact_rx rx
        JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        JOIN date_dim d ON rx.date_id = d.date_id
        WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
        """
        if specialty:
            sql += f" AND h.specialty ILIKE '%{specialty}%'"
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        if year:
            sql += f" AND d.year = {year}"
        if quarter:
            sql += f" AND d.quarter = '{quarter}'"
        sql += f" GROUP BY h.specialty, t.name ORDER BY total_{metric} DESC LIMIT 50"

    elif metric == "market_share":
        sql = f"""
        SELECT
            h.specialty,
            COUNT(DISTINCT h.hcp_id) AS hcp_count,
            ROUND(AVG(m.est_market_share), 2) AS avg_market_share,
            SUM(m.ln_patient_cnt) AS total_patients,
            t.name AS territory_name
        FROM fact_ln_metrics m
        JOIN hcp_dim h ON m.entity_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        WHERE m.entity_type = 'H'
        """
        if specialty:
            sql += f" AND h.specialty ILIKE '%{specialty}%'"
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        sql += " GROUP BY h.specialty, t.name ORDER BY avg_market_share DESC LIMIT 50"

    else:
        return f"Invalid metric: '{metric}'. Must be 'trx', 'nrx', or 'market_share'."

    try:
        results = execute_query(sql)
        if not results:
            return "No specialty analysis data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error computing specialty analysis: {str(e)}"

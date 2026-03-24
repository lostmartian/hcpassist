from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_hcp_ranking(
    metric: str = "trx",
    top_n: int = 10,
    direction: str = "top",
    territory: Optional[str] = None,
    specialty: Optional[str] = None,
    quarter: Optional[str] = None,
    year: Optional[int] = None,
) -> str:
    """Rank HCPs by a chosen metric — top or bottom performers.

    Example: "Top 10 prescribers" → get_hcp_ranking(metric="trx", top_n=10)
    Example: "Bottom 5 HCPs by market share in Territory 1" →
        get_hcp_ranking(metric="market_share", top_n=5, direction="bottom", territory="Territory 1")

    Args:
        metric: Ranking metric. One of: 'trx', 'nrx', 'market_share', 'patient_count'. Default: 'trx'.
        top_n: Number of results to return (1-50). Default: 10.
        direction: 'top' for highest or 'bottom' for lowest. Default: 'top'.
        territory: Filter by territory name. Optional.
        specialty: Filter by specialty. Optional.
        quarter: Filter by quarter ('Q1'-'Q4'). Optional. Used with trx/nrx.
        year: Filter by year. Optional. Used with trx/nrx.
    """
    top_n = min(max(top_n, 1), 50)
    order = "DESC" if direction == "top" else "ASC"

    if metric in ("trx", "nrx"):
        metric_col = "rx.trx_cnt" if metric == "trx" else "rx.nrx_cnt"
        sql = f"""
        SELECT
            h.full_name,
            h.specialty,
            h.tier,
            t.name AS territory_name,
            SUM({metric_col}) AS total_{metric}
        FROM fact_rx rx
        JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        JOIN date_dim d ON rx.date_id = d.date_id
        WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
        """
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        if specialty:
            sql += f" AND h.specialty ILIKE '%{specialty}%'"
        if quarter:
            sql += f" AND d.quarter = '{quarter}'"
        if year:
            sql += f" AND d.year = {year}"
        sql += f"""
        GROUP BY h.full_name, h.specialty, h.tier, t.name
        ORDER BY total_{metric} {order}
        LIMIT {top_n}
        """

    elif metric == "market_share":
        sql = f"""
        SELECT
            h.full_name,
            h.specialty,
            h.tier,
            t.name AS territory_name,
            AVG(m.est_market_share) AS avg_market_share,
            SUM(m.ln_patient_cnt) AS total_patients
        FROM fact_ln_metrics m
        JOIN hcp_dim h ON m.entity_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        WHERE m.entity_type = 'H'
        """
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        if specialty:
            sql += f" AND h.specialty ILIKE '%{specialty}%'"
        sql += f"""
        GROUP BY h.full_name, h.specialty, h.tier, t.name
        ORDER BY avg_market_share {order}
        LIMIT {top_n}
        """

    elif metric == "patient_count":
        sql = f"""
        SELECT
            h.full_name,
            h.specialty,
            h.tier,
            t.name AS territory_name,
            SUM(m.ln_patient_cnt) AS total_patients,
            AVG(m.est_market_share) AS avg_market_share
        FROM fact_ln_metrics m
        JOIN hcp_dim h ON m.entity_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        WHERE m.entity_type = 'H'
        """
        if territory:
            sql += f" AND t.name ILIKE '%{territory}%'"
        if specialty:
            sql += f" AND h.specialty ILIKE '%{specialty}%'"
        sql += f"""
        GROUP BY h.full_name, h.specialty, h.tier, t.name
        ORDER BY total_patients {order}
        LIMIT {top_n}
        """
    else:
        return f"Invalid metric: '{metric}'. Must be 'trx', 'nrx', 'market_share', or 'patient_count'."

    try:
        results = execute_query(sql)
        if not results:
            return f"No data found for HCP ranking by {metric}."
        return str(results)
    except Exception as e:
        return f"Error computing HCP ranking: {str(e)}"

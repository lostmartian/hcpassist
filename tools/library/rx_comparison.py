"""Prescription Comparison Tool.

Side-by-side Rx comparison across HCPs, territories, or time periods.
Join path: fact_rx → hcp_dim → territory_dim → date_dim
"""

from typing import Optional, List
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def compare_rx_performance(
    compare_by: str = "territory",
    metric: str = "trx",
    brand: str = "GAZYVA",
    quarter: Optional[str] = None,
    year: Optional[int] = None,
    territories: Optional[List[str]] = None,
    hcp_names: Optional[List[str]] = None,
) -> str:
    """Compare prescription performance side-by-side across entities or time periods.

    Example: "Compare TRx across all territories" → compare_rx_performance(compare_by="territory")
    Example: "Compare Dr. Garcia vs Dr. Lee NRx in Q1 2025" →
        compare_rx_performance(compare_by="hcp", metric="nrx", hcp_names=["Garcia", "Lee"],
                               quarter="Q1", year=2025)

    Args:
        compare_by: Comparison dimension — 'territory', 'hcp', 'specialty', or 'quarter'. Default: 'territory'.
        metric: 'trx' or 'nrx'. Default: 'trx'.
        brand: Brand code. Default: 'GAZYVA'.
        quarter: Filter by quarter. Optional.
        year: Filter by year. Optional.
        territories: List of territory names to compare. Optional (all if not specified).
        hcp_names: List of HCP names to compare. Optional.
    """
    metric_col = "rx.trx_cnt" if metric.lower() == "trx" else "rx.nrx_cnt"

    if compare_by == "territory":
        group_col = "t.name"
        group_alias = "territory_name"
    elif compare_by == "hcp":
        group_col = "h.full_name"
        group_alias = "hcp_name"
    elif compare_by == "specialty":
        group_col = "h.specialty"
        group_alias = "specialty"
    elif compare_by == "quarter":
        group_col = "d.year || '-' || d.quarter"
        group_alias = "period"
    else:
        return f"Invalid compare_by: '{compare_by}'. Must be 'territory', 'hcp', 'specialty', or 'quarter'."

    sql = f"""
    SELECT
        {group_col} AS {group_alias},
        SUM({metric_col}) AS total_{metric.lower()},
        COUNT(DISTINCT rx.hcp_id) AS hcp_count,
        ROUND(AVG({metric_col}), 2) AS avg_{metric.lower()}_per_record
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if brand:
        sql += f" AND rx.brand_code = '{brand}'"
    if quarter:
        sql += f" AND d.quarter = '{quarter}'"
    if year:
        sql += f" AND d.year = {year}"
    if territories:
        t_list = "', '".join(territories)
        sql += f" AND t.name IN ('{t_list}')"
    if hcp_names:
        name_conditions = []
        for name in hcp_names:
            clean = name.replace(".", "").replace(",", "").strip()
            fuzzy = "%".join(clean.split())
            name_conditions.append(f"h.full_name ILIKE '%{fuzzy}%'")
        sql += f" AND ({' OR '.join(name_conditions)})"

    sql += f" GROUP BY {group_col} ORDER BY total_{metric.lower()} DESC LIMIT 50"

    try:
        results = execute_query(sql)
        if not results:
            return "No comparison data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error comparing Rx performance: {str(e)}"

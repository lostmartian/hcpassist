import logging
from typing import Optional, List
from langchain_core.tools import tool
from db.connector import execute_query
from config import settings

logger = logging.getLogger(__name__)

@tool
def get_hcp_rx_performance(
    hcp_name: Optional[str] = None,
    territory: Optional[str] = None,
    specialty: Optional[str] = None,
    quarters: Optional[List[str]] = None,
    year: Optional[int] = None,
    brand: str = "GAZYVA",
    metric: str = "trx",
) -> str:
    """Get prescription performance (TRx/NRx) for specific HCPs, territories, or specialties.

    Example: "How many TRx did Dr. Blake Garcia write in Q1 2025?"
    -> get_hcp_rx_performance(hcp_name="Blake Garcia", quarters=["Q1"], year=2025)

    Args:
        hcp_name: Name or partial name of the HCP.
        territory: Name of the territory (e.g., 'Territory 1').
        specialty: HCP specialty (e.g., 'Nephrology').
        quarters: List of quarters (e.g., ['Q1', 'Q2']).
        year: Year (e.g., 2024 or 2025).
        brand: Pharmaceutical brand (default: 'GAZYVA').
        metric: 'trx' for total or 'nrx' for new prescriptions.
    """
    logger.info(f"HCP Rx Tool Params: hcp={hcp_name}, terr={territory}, quarters={quarters}, year={year}, brand={brand}, metric={metric}")

    metric_col = "rx.trx_cnt" if metric.lower() == "trx" else "rx.nrx_cnt"
    
    select_parts = [
        "h.full_name",
        "t.name as territory",
        "rx.brand_code",
        f"SUM({metric_col}) as total_{metric.lower()}",
    ]
    group_by_parts = ["h.full_name", "t.name", "rx.brand_code"]

    sql = f"""
    SELECT {', '.join(select_parts)}
    FROM fact_rx rx
    JOIN hcp_dim h ON rx.hcp_id = h.hcp_id
    JOIN territory_dim t ON h.territory_id = t.territory_id
    JOIN date_dim d ON rx.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if hcp_name:
        # Sanitize name
        clean_name = hcp_name.replace(".", "").replace(",", "").strip()
        fuzzy_name = "%".join(clean_name.split())
        sql += f" AND h.full_name ILIKE '%{fuzzy_name}%'"
    
    if territory:
        sql += f" AND t.name ILIKE '%{territory}%'"
    
    if specialty:
        sql += f" AND h.specialty = '{specialty}'"
    
    if brand:
        sql += f" AND rx.brand_code = '{brand}'"
    
    if quarters:
        q_list = "', '".join(quarters)
        sql += f" AND d.quarter IN ('{q_list}')"

    if year:
        sql += f" AND d.year = {year}"

    sql += f" GROUP BY {', '.join(group_by_parts)}"
    sql += f" ORDER BY total_{metric.lower()} DESC"
    sql += " LIMIT 50"

    logger.info(f"Executing HCP Rx SQL: {sql}")

    try:
        results = execute_query(sql)
        if not results:
            return "No prescription data found for the specified filters. Check if the HCP name or period is correct."
        return str(results)
    except Exception as e:
        logger.error(f"Error in get_hcp_rx_performance: {e}")
        return f"Error executing query: {e}"

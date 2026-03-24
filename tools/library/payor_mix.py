"""Account Payor Mix Tool.

Pre-defined SQL function for querying payment distribution at healthcare facilities.
Join path: fact_payor_mix → account_dim (account_id) → territory_dim (territory_id) → date_dim (date_id)
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_account_payor_mix(
    account_name: Optional[str] = None,
    account_type: Optional[str] = None,
    territory: Optional[str] = None,
    payor_type: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get the payor mix (payment distribution) for healthcare accounts/facilities.

    Shows the percentage breakdown of Commercial, Medicaid, Medicare, and Other payments.

    Args:
        account_name: Filter by account/facility name (e.g., 'Bay Hospital'). Optional.
        account_type: Filter by account type ('Hospital' or 'Clinic'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
        payor_type: Filter by payor type ('Commercial', 'Medicaid', 'Medicare', 'Other'). Optional.
        year: Filter by year (2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
    """
    sql = f"""
    SELECT
        acc.name AS account_name,
        acc.account_type,
        acc.address,
        t.name AS territory_name,
        pm.payor_type,
        AVG(pm.pct_of_volume) AS avg_pct_of_volume
    FROM fact_payor_mix pm
    JOIN account_dim acc ON pm.account_id = acc.account_id
    JOIN territory_dim t ON acc.territory_id = t.territory_id
    JOIN date_dim d ON pm.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """

    if account_name:
        clean_acc = account_name.replace(".", "").replace(",", "").strip()
        fuzzy_acc = "%".join(clean_acc.split())
        sql += f" AND acc.name ILIKE '%{fuzzy_acc}%'"
    if account_type:
        sql += f" AND acc.account_type = '{account_type}'"
    if territory:
        sql += f" AND t.name ILIKE '%{territory}%'"
    if payor_type:
        sql += f" AND pm.payor_type = '{payor_type}'"
    if year:
        sql += f" AND d.year = {year}"
    if quarter:
        sql += f" AND d.quarter = '{quarter}'"

    sql += """
    GROUP BY acc.name, acc.account_type, acc.address, t.name, pm.payor_type
    ORDER BY acc.name, avg_pct_of_volume DESC
    LIMIT 50
    """

    try:
        results = execute_query(sql)
        if not results:
            return "No payor mix data found for the specified filters."
        return str(results)
    except Exception as e:
        return f"Error executing query: {str(e)}"

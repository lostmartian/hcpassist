"""Account Payor Mix Tool.

Pre-defined SQL function for querying payment distribution at healthcare facilities.
Join path: fact_payor_mix → account_dim (account_id) → territory_dim (territory_id) → date_dim (date_id)

FIX (v2): When account_id is provided, aggregate across ALL rows for that account_id
          (regardless of location/territory sub-rows) so the answer is a single weighted
          average per payor type — matching the ground truth which is per-account-id, not
          per-facility-location.
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query
from config import settings


@tool
def get_account_payor_mix(
    account_name: Optional[str] = None,
    account_id: Optional[int] = None,
    account_type: Optional[str] = None,
    territory: Optional[str] = None,
    payor_type: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get the payor mix (payment distribution) for healthcare accounts/facilities.

    Shows the percentage breakdown of Commercial, Medicaid, Medicare, and Other payments.

    IMPORTANT: When a question references a specific account_id (e.g. 'Mountain Hospital
    account 1000'), pass account_id so that the result is aggregated across ALL locations
    of that account, giving a single percentage per payor type.

    Args:
        account_name: Filter by account/facility name (e.g., 'Bay Hospital'). Optional.
        account_id: Filter by exact account_id integer (e.g., 1000). Use this when the
                    question references a specific account ID. Gives a single aggregate
                    answer across all locations. Optional.
        account_type: Filter by account type ('Hospital' or 'Clinic'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
        payor_type: Filter by payor type ('Commercial', 'Medicaid', 'Medicare', 'Other'). Optional.
        year: Filter by year (2024 or 2025). Optional.
        quarter: Filter by quarter ('Q1', 'Q2', 'Q3', 'Q4'). Optional.
    """

    # ── When account_id is given, aggregate across ALL rows for that account ──
    # This produces ONE row per payor_type with a single weighted average,
    # matching the ground truth which is defined per account_id, not per sub-location.
    if account_id is not None:
        # If no specific time filter is given, default to the LATEST available date_id for this account
        time_filter = ""
        if year:
            time_filter += f" AND d.year = {year}"
        if quarter:
            time_filter += f" AND d.quarter = '{quarter}'"
        
        if not time_filter:
            # Default to latest data point
            latest_date_query = f"SELECT MAX(date_id) FROM fact_payor_mix WHERE account_id = {account_id}"
            time_filter = f" AND pm.date_id = ({latest_date_query})"

        sql = f"""
        SELECT
            acc.name AS account_name,
            acc.account_id,
            pm.payor_type,
            pm.pct_of_volume
        FROM fact_payor_mix pm
        JOIN account_dim acc ON pm.account_id = acc.account_id
        JOIN date_dim d ON pm.date_id = d.date_id
        WHERE pm.account_id = {account_id}
          AND d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
          {time_filter}
        """
        if payor_type:
            sql += f" AND pm.payor_type = '{payor_type}'"
        sql += """
        ORDER BY pct_of_volume DESC
        """
    else:
        # ── Without account_id: group by name+location+territory (detailed breakdown) ──
        sql = f"""
        SELECT
            acc.name AS account_name,
            acc.account_id,
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
        GROUP BY acc.name, acc.account_id, acc.account_type, acc.address, t.name, pm.payor_type
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

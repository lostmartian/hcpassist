from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_account_performance(
    account_name: Optional[str] = None,
    account_type: Optional[str] = None,
    territory: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
) -> str:
    """Get a comprehensive performance roll-up for accounts/facilities.

    Combines rep activity at the account, payor mix, and market share into one view.
    For Rx data tied to the account's HCPs, use get_hcp_rx_performance with territory filter.

    Example: "How is Mountain Hospital performing?" →
        get_account_performance(account_name="Mountain Hospital")

    Args:
        account_name: Filter by account name. Optional.
        account_type: 'Hospital' or 'Clinic'. Optional.
        territory: Filter by territory. Optional.
        year: Filter by year. Optional.
        quarter: Filter by quarter. Optional.
    """
    # Part 1: Activity summary per account
    act_sql = f"""
    SELECT
        acc.name AS account_name,
        acc.account_type,
        acc.address,
        t.name AS territory_name,
        COUNT(a.activity_id) AS total_rep_activities,
        SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed_activities,
        COUNT(DISTINCT a.rep_id) AS reps_visiting,
        COUNT(DISTINCT a.hcp_id) AS hcps_engaged
    FROM fact_rep_activity a
    JOIN account_dim acc ON a.account_id = acc.account_id
    JOIN territory_dim t ON acc.territory_id = t.territory_id
    JOIN date_dim d ON a.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """
    if account_name:
        clean = account_name.replace(".", "").replace(",", "").strip()
        fuzzy = "%".join(clean.split())
        act_sql += f" AND acc.name ILIKE '%{fuzzy}%'"
    if account_type:
        act_sql += f" AND acc.account_type ILIKE '%{account_type}%'"
    if territory:
        act_sql += f" AND t.name ILIKE '%{territory}%'"
    if year:
        act_sql += f" AND d.year = {year}"
    if quarter:
        act_sql += f" AND d.quarter = '{quarter}'"
    act_sql += " GROUP BY acc.name, acc.account_type, acc.address, t.name ORDER BY total_rep_activities DESC LIMIT 20"

    # Part 2: Payor mix per account
    pm_sql = f"""
    SELECT
        acc.name AS account_name,
        pm.payor_type,
        ROUND(AVG(pm.pct_of_volume), 1) AS avg_pct
    FROM fact_payor_mix pm
    JOIN account_dim acc ON pm.account_id = acc.account_id
    JOIN date_dim d ON pm.date_id = d.date_id
    WHERE d.calendar_date BETWEEN '{settings.DATA_WINDOW_START}' AND '{settings.DATA_WINDOW_END}'
    """
    if account_name:
        clean = account_name.replace(".", "").replace(",", "").strip()
        fuzzy = "%".join(clean.split())
        pm_sql += f" AND acc.name ILIKE '%{fuzzy}%'"
    if account_type:
        pm_sql += f" AND acc.account_type ILIKE '%{account_type}%'"
    if year:
        pm_sql += f" AND d.year = {year}"
    if quarter:
        pm_sql += f" AND d.quarter = '{quarter}'"
    pm_sql += " GROUP BY acc.name, pm.payor_type ORDER BY acc.name, avg_pct DESC"

    # Part 3: Market share per account (entity_type = 'A')
    ms_sql = """
    SELECT
        acc.name AS account_name,
        m.quarter_id,
        m.ln_patient_cnt,
        m.est_market_share
    FROM fact_ln_metrics m
    JOIN account_dim acc ON m.entity_id = acc.account_id
    WHERE m.entity_type = 'A'
    """
    if account_name:
        clean = account_name.replace(".", "").replace(",", "").strip()
        fuzzy = "%".join(clean.split())
        ms_sql += f" AND acc.name ILIKE '%{fuzzy}%'"
    ms_sql += " ORDER BY m.quarter_id DESC LIMIT 20"

    try:
        activity_data = execute_query(act_sql)
        payor_data = execute_query(pm_sql)
        market_data = execute_query(ms_sql)

        output = {
            "activity_summary": activity_data,
            "payor_mix": payor_data,
            "market_share": market_data,
        }

        if not activity_data and not payor_data and not market_data:
            return "No performance data found for the specified account filters."
        return str(output)
    except Exception as e:
        return f"Error computing account performance: {str(e)}"

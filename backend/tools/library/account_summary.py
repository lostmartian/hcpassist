"""Account Profile Lookup Tool.

Search and retrieve account/facility profiles.
Join path: account_dim → territory_dim (territory_id)
No fact tables — purely dimensional lookup.
"""

from typing import Optional
from langchain_core.tools import tool

from db.connector import execute_query


@tool
def get_account_profile(
    account_name: Optional[str] = None,
    account_type: Optional[str] = None,
    territory: Optional[str] = None,
) -> str:
    """Look up account/facility profiles and details.

    Returns name, type, address, and territory for matching accounts.
    Does NOT include Rx or payor data — use get_account_performance or
    get_account_payor_mix for that.

    Example: "Tell me about Mountain Hospital" → get_account_profile(account_name="Mountain Hospital")
    Example: "List all clinics in Territory 2" → get_account_profile(account_type="Clinic", territory="Territory 2")

    Args:
        account_name: Full or partial account name (e.g., 'Bay Hospital'). Optional.
        account_type: Filter by account type ('Hospital' or 'Clinic'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
    """
    sql = """
    SELECT
        acc.account_id,
        acc.name AS account_name,
        acc.account_type,
        acc.address,
        t.name AS territory_name,
        t.geo_type
    FROM account_dim acc
    JOIN territory_dim t ON acc.territory_id = t.territory_id
    WHERE 1=1
    """

    if account_name:
        clean_name = account_name.replace(".", "").replace(",", "").strip()
        fuzzy_name = "%".join(clean_name.split())
        sql += f" AND acc.name ILIKE '%{fuzzy_name}%'"
    if account_type:
        sql += f" AND acc.account_type ILIKE '%{account_type}%'"
    if territory:
        sql += f" AND t.name ILIKE '%{territory}%'"

    sql += " ORDER BY acc.name LIMIT 50"

    try:
        results = execute_query(sql)
        if not results:
            return "No accounts found matching the specified criteria."
        return str(results)
    except Exception as e:
        return f"Error looking up account profiles: {str(e)}"

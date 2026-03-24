from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query


@tool
def get_hcp_profile(
    hcp_name: Optional[str] = None,
    specialty: Optional[str] = None,
    tier: Optional[str] = None,
    territory: Optional[str] = None,
) -> str:
    """Look up HCP (Healthcare Professional) profiles and demographics.

    Returns name, specialty, tier, and territory for matching HCPs.
    Does NOT include prescription data — use get_hcp_rx_performance for that.

    Example: "Who is Dr. Blake Garcia?" → get_hcp_profile(hcp_name="Blake Garcia")
    Example: "List all Tier A oncologists" → get_hcp_profile(specialty="Oncology", tier="A")

    Args:
        hcp_name: Full or partial name of the HCP (e.g., 'Garcia'). Optional.
        specialty: Filter by medical specialty (e.g., 'Rheumatology', 'Oncology'). Optional.
        tier: Filter by HCP tier ('A', 'B', 'C'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
    """
    sql = """
    SELECT
        h.hcp_id,
        h.full_name,
        h.specialty,
        h.tier,
        t.name AS territory_name,
        t.geo_type
    FROM hcp_dim h
    JOIN territory_dim t ON h.territory_id = t.territory_id
    WHERE 1=1
    """

    if hcp_name:
        clean_name = hcp_name.replace(".", "").replace(",", "").strip()
        fuzzy_name = "%".join(clean_name.split())
        sql += f" AND h.full_name ILIKE '%{fuzzy_name}%'"
    if specialty:
        sql += f" AND h.specialty ILIKE '%{specialty}%'"
    if tier:
        sql += f" AND h.tier = '{tier.upper()}'"
    if territory:
        sql += f" AND t.name ILIKE '%{territory}%'"

    sql += " ORDER BY h.full_name LIMIT 50"

    try:
        results = execute_query(sql)
        if not results:
            return "No HCPs found matching the specified criteria."
        return str(results)
    except Exception as e:
        return f"Error looking up HCP profiles: {str(e)}"

"""Market Share & Patient Metrics Tool.

Pre-defined SQL function for querying market share and patient counts.
Join path: POLYMORPHIC — depends on entity_type:
  - entity_type = 'H' → fact_ln_metrics.entity_id joins hcp_dim.hcp_id
  - entity_type = 'A' → fact_ln_metrics.entity_id joins account_dim.account_id

This is the TRICKIEST join in the dataset. A naive single join will produce wrong results.
"""

from typing import Optional
from langchain_core.tools import tool

from backend.db.connector import execute_query
from backend.config import settings


@tool
def get_market_share_metrics(
    entity_type: Optional[str] = None,
    entity_name: Optional[str] = None,
    quarter_id: Optional[str] = None,
    territory: Optional[str] = None,
) -> str:
    """Get market share and patient count metrics for HCPs or Accounts.

    IMPORTANT: entity_type determines the join target:
    - 'H' (HCP): joins to hcp_dim for doctor-level metrics
    - 'A' (Account): joins to account_dim for facility-level metrics

    Args:
        entity_type: 'H' for HCP or 'A' for Account. If not specified, returns both.
        entity_name: Filter by entity name (HCP full_name or account name). Optional.
        quarter_id: Filter by quarter ID (e.g., '2024Q4', '2025Q1'). Optional.
        territory: Filter by territory name (e.g., 'Territory 1'). Optional.
    """
    allowed_quarters = settings.ALLOWED_QUARTERS

    if quarter_id and quarter_id not in allowed_quarters:
        return f"Invalid quarter_id: '{quarter_id}'. Allowed values: {allowed_quarters}"

    results = []

    # Query HCP-level metrics
    if entity_type is None or entity_type.upper() == "H":
        hcp_sql = f"""
        SELECT
            'HCP' AS entity_category,
            h.full_name AS entity_name,
            h.specialty,
            h.tier,
            t.name AS territory_name,
            m.quarter_id,
            m.ln_patient_cnt,
            m.est_market_share
        FROM fact_ln_metrics m
        JOIN hcp_dim h ON m.entity_id = h.hcp_id
        JOIN territory_dim t ON h.territory_id = t.territory_id
        WHERE m.entity_type = 'H'
        """
        if entity_name:
            clean_name = entity_name.replace(".", "").replace(",", "").strip()
            fuzzy_name = "%".join(clean_name.split())
            hcp_sql += f" AND h.full_name ILIKE '%{fuzzy_name}%'"
        if quarter_id:
            hcp_sql += f" AND m.quarter_id = '{quarter_id}'"
        if territory:
            hcp_sql += f" AND t.name ILIKE '%{territory}%'"
        hcp_sql += " ORDER BY m.est_market_share DESC LIMIT 50"

        try:
            results.extend(execute_query(hcp_sql))
        except Exception as e:
            results.append({"error": f"HCP query failed: {str(e)}"})

    # Query Account-level metrics
    if entity_type is None or entity_type.upper() == "A":
        acc_sql = f"""
        SELECT
            'Account' AS entity_category,
            acc.name AS entity_name,
            acc.account_type,
            acc.address,
            t.name AS territory_name,
            m.quarter_id,
            m.ln_patient_cnt,
            m.est_market_share
        FROM fact_ln_metrics m
        JOIN account_dim acc ON m.entity_id = acc.account_id
        JOIN territory_dim t ON acc.territory_id = t.territory_id
        WHERE m.entity_type = 'A'
        """
        if entity_name:
            clean_name = entity_name.replace(".", "").replace(",", "").strip()
            fuzzy_name = "%".join(clean_name.split())
            acc_sql += f" AND acc.name ILIKE '%{fuzzy_name}%'"
        if quarter_id:
            acc_sql += f" AND m.quarter_id = '{quarter_id}'"
        if territory:
            acc_sql += f" AND t.name ILIKE '%{territory}%'"
        acc_sql += " ORDER BY m.est_market_share DESC LIMIT 50"

        try:
            results.extend(execute_query(acc_sql))
        except Exception as e:
            results.append({"error": f"Account query failed: {str(e)}"})

    if not results:
        return "No market share data found for the specified filters."
    return str(results)

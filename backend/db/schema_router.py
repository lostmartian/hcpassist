import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Map keywords to tables in the schema
KEYWORD_MAPPING = {
    "hcp": ["hcp_dim"],
    "provider": ["hcp_dim"],
    "doctor": ["hcp_dim"],
    "rx": ["fact_rx"],
    "prescription": ["fact_rx"],
    "trx": ["fact_rx"],
    "nrx": ["fact_rx"],
    "volume": ["fact_rx"],
    "account": ["account_dim"],
    "hospital": ["account_dim"],
    "facility": ["account_dim"],
    "clinic": ["account_dim"],
    "rep": ["rep_dim", "fact_rep_activity"],
    "representative": ["rep_dim", "fact_rep_activity"],
    "activity": ["fact_rep_activity"],
    "payor": ["fact_payor_mix"],
    "insurance": ["fact_payor_mix"],
    "medicare": ["fact_payor_mix"],
    "medicaid": ["fact_payor_mix"],
    "commercial": ["fact_payor_mix"],
    "territory": ["territory_dim", "hcp_dim"],
    "region": ["territory_dim", "rep_dim"],
    "market": ["fact_ln_metrics"],
    "share": ["fact_ln_metrics"],
    "patient": ["fact_ln_metrics"],
    "trend": ["fact_rx", "date_dim"],
    "growth": ["fact_rx", "fact_ln_metrics"],
}

# Always include date_dim if any fact table is included
FACT_TABLES = ["fact_rx", "fact_rep_activity", "fact_payor_mix", "fact_ln_metrics"]

def get_relevant_schema(query: str, full_schema: Dict[str, Any]) -> str:
    """
    Given a user query and the full schema, return a pruned JSON string
    containing only the relevant tables.
    """
    relevant_tables = set()
    query_lower = query.lower()
    
    for kw, tables in KEYWORD_MAPPING.items():
        if kw in query_lower:
            relevant_tables.update(tables)
            
    # Heuristic: if any fact table is present, we almost always need date_dim
    if any(ft in relevant_tables for ft in FACT_TABLES):
        relevant_tables.add("date_dim")
        
    # If no keywords matched, return a minimal set or nothing to save tokens
    if not relevant_tables:
        logger.info("No relevant tables found for query, returning empty schema.")
        return "{}"

    pruned_schema = {t: full_schema[t] for t in relevant_tables if t in full_schema}
    
    logger.info(f"Pruned schema to {len(pruned_schema)} tables: {list(pruned_schema.keys())}")
    return json.dumps(pruned_schema, indent=2)

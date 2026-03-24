import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config import settings
from graph.state import AgentState
from utils.clean_content import extract_text_content

logger = logging.getLogger(__name__)
_guard_llm = None

def get_guard_llm():
    """Lazily initialize the Guard LLM."""
    global _guard_llm
    if _guard_llm is None:
        _guard_llm = ChatGoogleGenerativeAI(
            model=settings.RESPONDER_MODEL,  # Use a fast model for guarding
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
    return _guard_llm

GUARD_PROMPT = """You are a security and privacy filter for a data analysis platform. 
Your task is to take the provided final response and ensure it contains NO technical details from the database schema.

**STRICT RULES:**
1. Remove all literal table names (e.g., `hcp_dim`, `fact_rx`, `account_dim`, etc.).
2. Remove any references to column data types (e.g., `VARCHAR`, `INTEGER`, `FLOAT`).
3. Remove any raw SQL query snippets or join conditions.
4. If table/column names are mentioned, rephrase them into plain English (e.g., "The HCP list" instead of "the hcp_dim table").
5. Format the result as a professional Markdown analysis. Use tables where appropriate.
6. If the response is already clean, return it exactly as is.

**FINAL RESPONSE TO CHECK:**
{final_response}

Return the sanitized, professionally formatted version of the response below.
"""

def guard_node(state: AgentState) -> dict:
    llm = get_guard_llm()
    final_response = state.get("final_response", "")
    
    if not final_response:
        return {}

    prompt = GUARD_PROMPT.format(final_response=final_response)
    response = llm.invoke([HumanMessage(content=prompt)])
    content = extract_text_content(response.content)
    sanitized = content.strip()

    logger.info("Guard node completed sanitization check")
    return {"final_response": sanitized}

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

GUARD_PROMPT = """You are a security and privacy filter for a pharmaceutical data platform.
Your task is to take the provided final response and ensure it adheres to professional and security standards.

**STRICT RULES:**
1. DATA PRIVACY: Remove all literal table names (e.g., `hcp_dim`, `fact_rx`), column types, or raw SQL snippets.
2. SCOPE ENFORCEMENT: If the response contains any off-topic information (Stock prices, Competitor comparisons not in our data, Web scraping scripts, Destructive SQL attempts), you MUST REPLACE the entire response with a polite refusal: "I can only assist with internal pharmaceutical data analysis for GAZYVA. I cannot provide real-time market data, competitor comparisons, or execute system-level scripts."
3. NO HALLUCINATIONS: If the data retrieved was empty or indicated an error, do NOT fabricate a standard report. Instead, state: "The requested data is not available in the current dataset."
4. FORMATTING: Ensure the output is clean Markdown with professional headers.

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

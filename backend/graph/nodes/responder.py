import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from config import settings
from graph.state import AgentState
from utils.clean_content import extract_text_content

logger = logging.getLogger(__name__)

_responder_llm = None


def get_responder_llm():
    """Lazily initialize the Responder LLM."""
    global _responder_llm
    if _responder_llm is None:
        _responder_llm = ChatGoogleGenerativeAI(
            model=settings.RESPONDER_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
    return _responder_llm


RESPONDER_PROMPT = """You are a professional data analyst for a pharmaceutical platform. 
Convert the provided raw data into a clean, insightful Markdown report for an executive audience.

**STRICT FORMATTING RULES:**
1. ALWAYS use professional Markdown tables for any tabular or list-based data.
2. Structure the response with a concise introductory paragraph followed by the data summary.
3. Use descriptive, user-friendly headers in your tables (e.g., "Provider Name" instead of "hcp_id" or "full_name").
4. Round numeric values to 2 decimal places and use bold (**example**) for key metrics.
5. NEVER mention internal technical details like table names (hcp_dim, fact_rx), column names, or RAG source paths.
6. Use bullet points for any non-tabular qualitative insights.

**USER QUESTION:**
{question}

**RAW DATA:**
{data}

Provide the clean analytical report below.
"""


def responder_node(state: AgentState) -> dict:
    llm = get_responder_llm()
    user_question = ""
    for msg in state["messages"]:
        if hasattr(msg, "type") and msg.type == "human":
            user_question = msg.content
    tool_data = state.get("last_tool_result", "")

    prompt = RESPONDER_PROMPT.format(question=user_question, data=tool_data)

    response = llm.invoke([HumanMessage(content=prompt)])
    content = extract_text_content(response.content)
    formatted = content.strip()

    logger.info(f"Responder generated {len(formatted)} chars of Markdown")

    return {"final_response": formatted}

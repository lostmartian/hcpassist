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


RESPONDER_PROMPT = """You are a data response formatter. Convert the raw data below into a clean, professional Markdown response.

## STRICT RULES
1. Output ONLY valid, parsable Markdown.
2. Answer ONLY what was asked. Do NOT add extra insights, suggestions, or commentary.
3. Use Markdown tables for tabular data.
4. Use bullet points for lists.
5. Use bold for key metrics and numbers.
6. Do NOT start with phrases like "Here is..." or "Based on the data...". Go straight to the answer.
7. If the data shows no results, state that clearly and concisely.
8. Round decimal numbers to 2 decimal places.
9. Do NOT include any SQL queries or technical details in the response.

## USER QUESTION
{question}

## RAW DATA FROM DATABASE
{data}

Format this data into a clean Markdown response answering the user's question.
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

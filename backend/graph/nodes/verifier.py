import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

from config import settings
from graph.state import AgentState
from utils.clean_content import extract_text_content

logger = logging.getLogger(__name__)
_verifier_llm = None

def get_verifier_llm():
    """Lazily initialize the Verifier LLM."""
    global _verifier_llm
    if _verifier_llm is None:
        _verifier_llm = ChatGoogleGenerativeAI(
            model=settings.VERIFIER_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
    return _verifier_llm


VERIFICATION_PROMPT = """You are a data verification specialist. Your task is to check if tool results indicate an error or if the data retrieval was successful.

Review the conversation above. The last message(s) contain tool results.

Check:
1. Did any tool return an ERROR message?
2. Did any tool return "No data found" or empty results?
3. Were there any SQL execution failures?

Respond with EXACTLY one of:
- "PASS" if the tool executed successfully and returned meaningful data
- "FAIL: <reason>" if there was an error or the results are empty/invalid

Do NOT add any other text.
"""

def verifier_node(state: AgentState) -> dict:
    llm = get_verifier_llm()
    # Prompt Caching Optimization: instruction first
    messages = [SystemMessage(content=VERIFICATION_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    content = extract_text_content(response.content)
    result = content.strip()

    logger.info(f"Verifier result: {result}")

    if result.startswith("PASS"):
        return {
            "verification_passed": True,
            "last_tool_result": _extract_last_tool_result(state),
        }
    else:
        new_retry = state.get("retry_count", 0) + 1
        logger.warning(f"Verification FAILED (attempt {new_retry}/{settings.MAX_RETRIES}): {result}")
        return {
            "verification_passed": False,
            "retry_count": new_retry,
            "messages": [
                HumanMessage(
                    content=f"The previous attempt failed verification: {result}. "
                    f"Please try a different approach. Retry {new_retry}/{settings.MAX_RETRIES}."
                )
            ],
        }


def _extract_last_tool_result(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "tool":
            return msg.content
    return ""

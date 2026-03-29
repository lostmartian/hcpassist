from langchain_core.messages import HumanMessage, SystemMessage
from graph.state import AgentState
from graph.agents import get_llm

logger = logging.getLogger(__name__)

# System instructions (Fixed for caching)
REFLECTION_INST = """You are a Diagnostic Introspector for a pharmaceutical AI.
The previous tool execution returned an error or insufficient data.

Analyze the tool outputs and the original query.
Identify:
1. What went wrong? (e.g., column doesn't exist, date out of range, no results for filter)
2. How to fix it? (e.g., use a different tool, adjust date range, check spelling of HCP)

Provide a concise feedback message to the Supervisor for the next planning step.
"""

def introspect_node(state: AgentState) -> dict:
    llm = get_llm()
    
    # Prompt Caching Optimization: instruction first
    messages = [SystemMessage(content=REFLECTION_INST)] + state["messages"]
    
    response = llm.invoke(messages)
    
    feedback = response.content
    logger.info(f"Introspection Feedback: {feedback[:100]}...")
    
    return {
        "introspective_feedback": feedback,
        "retry_count": state.get("retry_count", 0) + 1
    }

import logging
from langchain_core.messages import SystemMessage
from graph.state import AgentState
from graph.agents import get_llm, PHARMA_RESEARCHER_PROMPT, PHARMA_RESEARCHER_TOOLS

logger = logging.getLogger(__name__)

def pharma_researcher_node(state: AgentState) -> dict:
    llm = get_llm().bind_tools(PHARMA_RESEARCHER_TOOLS)
    
    sys_msg = SystemMessage(content=PHARMA_RESEARCHER_PROMPT)
    messages = [sys_msg] + state["messages"]
    
    response = llm.invoke(messages)
    
    logger.info(f"Pharma Researcher response: {response.content[:100] if response.content else 'tool_call'}")
    
    return {"messages": [response]}

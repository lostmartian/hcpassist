import logging
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import AgentState
from graph.agents import get_llm, SUPERVISOR_PROMPT

logger = logging.getLogger(__name__)

class RouterOutput(BaseModel):
    next_agent: Literal["Data_Analyst", "Pharma_Researcher", "FINISH"] = Field(
        description="The next agent to act, or FINISH if the task is complete."
    )
    plan: list[str] = Field(description="Step-by-step plan for the current query.")

def supervisor_node(state: AgentState) -> dict:
    llm = get_llm().with_structured_output(RouterOutput)
    
    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
    
    response = llm.invoke(messages)
    
    logger.info(f"Supervisor decision: {response.next_agent} | Plan: {response.plan}")
    
    return {
        "next_agent": response.next_agent,
        "plan": response.plan
    }

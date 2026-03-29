import logging
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from graph.state import AgentState
from graph.agents import DATA_ANALYST_TOOLS, PHARMA_RESEARCHER_TOOLS
from graph.nodes.supervisor import supervisor_node
from graph.nodes.data_analyst import data_analyst_node
from graph.nodes.pharma_researcher import pharma_researcher_node
from graph.nodes.introspector import introspect_node
from graph.nodes.verifier import verifier_node
from graph.nodes.responder import responder_node
from graph.nodes.guard import guard_node

logger = logging.getLogger(__name__)

# Combine all tools for the ToolNode
ALL_TOOLS = DATA_ANALYST_TOOLS + PHARMA_RESEARCHER_TOOLS

def route_supervisor(state: AgentState) -> str:
    return state.get("next_agent", "FINISH")

def route_verifier(state: AgentState) -> str:
    if state.get("verification_passed", False):
        return "supervisor"
    return "introspector"

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("pharma_researcher", pharma_researcher_node)
    workflow.add_node("executer", ToolNode(ALL_TOOLS))
    workflow.add_node("introspector", introspect_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("responder", responder_node)
    workflow.add_node("guard", guard_node)
    
    # Build Edges
    workflow.set_entry_point("supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "Data_Analyst": "data_analyst",
            "Pharma_Researcher": "pharma_researcher",
            "FINISH": "responder"
        }
    )
    
    workflow.add_edge("data_analyst", "executer")
    workflow.add_edge("pharma_researcher", "executer")
    workflow.add_edge("executer", "verifier")
    
    workflow.add_conditional_edges(
        "verifier",
        route_verifier,
        {
            "supervisor": "supervisor",
            "introspector": "introspector"
        }
    )
    
    workflow.add_edge("introspector", "supervisor")
    workflow.add_edge("responder", "guard")
    workflow.add_edge("guard", END)
    
    workflow_compiled = workflow.compile()
    logger.info("Multi-Agent Graph compiled successfully")
    return workflow_compiled
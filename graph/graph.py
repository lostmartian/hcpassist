import logging
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from configm import settings
from tools.library.hcp_lookup import get_hcp_profile
from tools.library.hcp_rx import get_hcp_rx_performance
from tools.library.account_summary import get_account_profile
from tools.library.payor_mix import get_account_payor_mix
from tools.library.rep_activity import get_rep_activity_summary
from tools.library.date_range import get_date_info
from tools.library.hcp_ranking import get_hcp_ranking
from tools.library.rx_trend import get_rx_trend
from tools.library.rx_comparison import compare_rx_performance
from tools.library.rep_performance import get_rep_performance
from tools.library.specialty_analysis import get_specialty_analysis
from tools.library.market_share import get_market_share_metrics
from tools.library.territory import get_territory_summary
from tools.library.rep_hcp_coverage import get_rep_hcp_coverage
from tools.library.account_performance import get_account_performance
from tools.library.kpi_dashboard import get_kpi_dashboard
from tools.library.growth_analysis import get_growth_analysis
from tools.fallback_sql import execute_safe_sql

from graph.nodes.planner import planner_node, get_planner_llm, get_system_prompt
from graph.nodes.verifier import verifier_node
from graph.nodes.responder import responder_node

from rag.retriever import search_doc

from utils import extract_text_content

logger = logging.getLogger(__name__)

ALL_TOOLS_LIST = [
    get_hcp_profile,
    get_hcp_rx_performance,
    get_account_profile,
    get_account_payor_mix,
    get_rep_activity_summary,
    get_date_info,
    get_hcp_ranking,
    get_rx_trend,
    compare_rx_performance,
    get_rep_performance,
    get_specialty_analysis,
    get_market_share_metrics,
    get_territory_summary,
    get_rep_hcp_coverage,
    get_account_performance,
    get_kpi_dashboard,
    get_growth_analysis,
    search_doc,
    execute_safe_sql,
]

def planner_with_tools(state: AgentState, llm_with_tools) -> dict:
    sys_msg = SystemMessage(content=get_system_prompt())
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    content = extract_text_content(response.content)
    logger.info(f"Planner response: {content[:200] if content else 'tool_call'}")
    return {"messages": [response]}

def after_planner(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "executer"
    return "responder"

def after_verifier(state: AgentState) -> str:
    if state.get("verification_passed", False):
        return "responder"
    if state.get("retry_count", 0) >= settings.MAX_RETRIES:
        logger.warning("Max retries reached. Ending graph.")
        return "responder"
    return "planner"

def build_graph():
    llm = get_planner_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS_LIST)
    tool_node = ToolNode(tools=ALL_TOOLS_LIST)

    workflow = StateGraph(AgentState)
    workflow.add_node("planner", lambda state: planner_with_tools(state, llm_with_tools))
    workflow.add_node("executer", tool_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("responder", responder_node)

    """
    planner -> executer -> verifier -> responder -> END
            -> responder
    if verifier fails -> planner
    if verifier fails and max retries reached -> responder
    """
    workflow.set_entry_point("planner")
    workflow.add_conditional_edges(
        "planner", 
        after_planner,
        {
            "executer": "executer",
            "responder": "responder"
        }
    )
    workflow.add_edge("executer", "verifier")
    workflow.add_conditional_edges(
        "verifier",
        after_verifier,
        {
            "planner": "planner",
            "responder": "responder"
        }
    )
    workflow.add_edge("responder", END)

    workflow_compiled = workflow.compile()
    logger.info("Graph compiled successfully")
    return workflow_compiled
from graph.agents import get_llm, DATA_ANALYST_PROMPT, DATA_ANALYST_TOOLS
from db.connector import get_schema_snapshot
from db.schema_router import get_relevant_schema

logger = logging.getLogger(__name__)

def data_analyst_node(state: AgentState) -> dict:
    llm = get_llm().bind_tools(DATA_ANALYST_TOOLS)
    
    # Get the original user question to prune the schema
    user_question = ""
    for msg in state["messages"]:
        if hasattr(msg, "type") and msg.type == "human":
            user_question = msg.content
            break
            
    # Dynamic Schema Pruning
    full_schema = get_schema_snapshot()
    pruned_schema = get_relevant_schema(user_question, full_schema)
    
    # Build System Prompt with Dynamic Schema
    dynamic_prompt = f"{DATA_ANALYST_PROMPT}\n\n## DATABASE SCHEMA (Relevant Tables Only)\n{pruned_schema}"
    
    sys_msg = SystemMessage(content=dynamic_prompt)
    
    # Prompt Caching Optimization: Put the SystemMessage FIRST
    messages = [sys_msg] + state["messages"]
    
    response = llm.invoke(messages)
    
    logger.info(f"Data Analyst response: {response.content[:100] if response.content else 'tool_call'}")
    
    return {"messages": [response]}

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    last_tool_result: Optional[str]
    verification_passed: bool
    final_response: Optional[str]
    plan: Optional[List[str]]
    intermediate_results: Dict[str, Any]
    next_agent: Optional[str]
    introspective_feedback: Optional[str]
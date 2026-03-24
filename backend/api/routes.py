import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from graph.graph import build_graph

logger = logging.getLogger(__name__)

router = APIRouter()

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    retry_count: int = 0

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    graph = get_graph()
    init_state = {
        "messages": [HumanMessage(content=request.message)],
        "retry_count": 0,
        "last_tool_result": None,
        "verification_flag": False,
        "final_response": None,
    }

    try:
        result = await asyncio.to_thread(graph.invoke, init_state)
        answer = result.get("final_response") or "Unable to generate response"
        retry_count = result.get("retry_count", 0)
        logger.info(f"Retry count: {retry_count}")
        return ChatResponse(
            response=answer,
            retry_count=retry_count,
        )
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    
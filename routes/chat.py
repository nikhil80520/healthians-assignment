"""
chat.py — Chat Endpoint Route
"""

import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent import process_message, stream_message
from models import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard synchronous chat endpoint.
    Still works using the fallback method in agent.py.
    """
    response = await process_message(
        user_message=request.user_message,
        session_id=request.session_id,
        phone=request.phone_number,
        language=request.language,
    )
    return response

@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    """
    async def event_generator():
        try:
            async for chunk in stream_message(
                user_message=request.user_message,
                session_id=request.session_id,
                phone=request.phone_number,
                language=request.language,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_chunk = {"type": "token", "content": "\n\n**Error**: An unexpected error occurred while generating the response."}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

"""
routes/chat.py — Chat API Endpoint
POST /api/v1/chat — Main conversation endpoint for the Healthians AI assistant.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from agent import process_message
from models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse, summary="Chat with Healthians AI")
async def chat_endpoint(request: ChatRequest):
    """
    Send a message to the Healthians AI assistant and receive a structured response.

    - **user_message**: The user's chat message (required)
    - **session_id**: Unique session identifier for conversation continuity (required)
    - **phone_number**: Optional 10-digit phone number for fetching reports / context
    - **language**: Preferred response language — 'en', 'hi', or 'auto' (default)
    """
    try:
        response = await process_message(
            user_message=request.user_message,
            session_id=request.session_id,
            phone=request.phone_number,
            language=request.language,
        )
        return response

    except Exception as e:
        logger.error(f"Unhandled error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        )

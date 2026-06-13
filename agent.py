"""
agent.py — Core AI Logic using LangGraph's create_react_agent
Handles streaming and session persistence.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
from langgraph.prebuilt import create_react_agent
from langchain_aws import ChatBedrockConverse

from config import settings
from models import ChatResponse
from prompts import SYSTEM_PROMPT
from sessions import add_message
from tools import (
    answer_faq,
    book_appointment,
    escalate_to_doctor,
    explain_report,
    fetch_reports,
    get_packages,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Streaming Entry Point
# ---------------------------------------------------------------------------

async def stream_message(
    user_message: str,
    session_id: str,
    phone: str | None = None,
    language: str = "auto",
):
    """Stream agent response token-by-token and yield tool events."""
    
    sys_override = ""
    if language == "hi":
        sys_override += "\n\n[LANGUAGE OVERRIDE: Respond in Hindi (Devanagari script). Keep medical terms in English.]"
    elif language == "en":
        sys_override += "\n\n[LANGUAGE OVERRIDE: Respond in English only.]"
    
    if phone:
        sys_override += f"\n\n[USER CONTEXT: Registered phone number is {phone}]"
        
    from datetime import datetime
    current_date = datetime.now().strftime("%d-%m-%Y %H:%M")
    sys_override += f"\n\n[SYSTEM CONTEXT: The current date and time is {current_date}. Use this to resolve relative dates like 'tomorrow'.]"
    
    messages = []
    if sys_override:
        messages.append(SystemMessage(content=sys_override))
    messages.append(HumanMessage(content=user_message))
    
    config = {"configurable": {"thread_id": session_id}}
    
    kwargs = {
        "model": settings.MODEL_NAME,
        "region_name": settings.AWS_REGION,
        "max_tokens": settings.MAX_TOKENS,
        "temperature": settings.TEMPERATURE,
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        
    llm = ChatBedrockConverse(**kwargs)
    
    tools = [
        explain_report,
        book_appointment,
        fetch_reports,
        answer_faq,
        escalate_to_doctor,
        get_packages,
    ]
    
    final_reply = ""
    tool_data = None

    async with AsyncSqliteSaver.from_conn_string("healthians_sessions.db") as checkpointer:
        await checkpointer.setup()
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )
        
        # astream_events yields token-by-token and tool callbacks natively
        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2"
        ):
            kind = event["event"]
            
            # Stream LLM tokens
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    text = ""
                    if isinstance(chunk.content, str):
                        text = chunk.content
                    elif isinstance(chunk.content, list):
                        for item in chunk.content:
                            if isinstance(item, dict) and "text" in item:
                                text += item["text"]
                            elif isinstance(item, str):
                                text += item
                    
                    if text:
                        yield {"type": "token", "content": text}
                        final_reply += text
                    
            # Emit when a tool starts executing
            elif kind == "on_tool_start":
                tool_name = event["name"]
                yield {"type": "tool_call", "tools": [tool_name]}
                
            # Catch tool output
            elif kind == "on_tool_end":
                output = event["data"].get("output")
                if output:
                    try:
                        if hasattr(output, 'content'):
                            tool_data = json.loads(output.content)
                        elif isinstance(output, str):
                            tool_data = json.loads(output)
                        else:
                            tool_data = output
                    except:
                        pass

    # Save to custom SQLite database for analytics/audit
    await add_message(session_id, "user", user_message)
    await add_message(session_id, "assistant", final_reply, tool_data)


# ---------------------------------------------------------------------------
# Synchronous / Blocking Entry Point (Fallback)
# ---------------------------------------------------------------------------

async def process_message(
    user_message: str,
    session_id: str,
    phone: str | None = None,
    language: str = "auto",
) -> ChatResponse:
    """Fallback blocking function for legacy code."""
    reply = ""
    intent = "general_chat"
    
    async for chunk in stream_message(user_message, session_id, phone, language):
        if chunk["type"] == "token":
            reply += chunk["content"]
        elif chunk["type"] == "tool_call":
            intent = chunk["tools"][0]
            
    return ChatResponse(
        reply=reply,
        intent=intent,
        data=None,
        suggested_followups=[],
        session_id=session_id
    )

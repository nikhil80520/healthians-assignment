"""
agent.py — Core AI Logic for Healthians AI
Handles LangChain tool calling via ChatBedrockConverse.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_aws import ChatBedrockConverse

from config import settings
from models import ChatResponse
from prompts import SYSTEM_PROMPT
from sessions import add_message, get_session
from tools import (
    answer_faq,
    book_appointment,
    escalate_to_doctor,
    explain_report,
    fetch_reports,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangChain LLM Init
# ---------------------------------------------------------------------------

def _get_llm():
    """Create ChatBedrockConverse instance."""
    kwargs = {
        "model": settings.MODEL_NAME,
        "region_name": settings.AWS_REGION,
        "max_tokens": settings.MAX_TOKENS,
        "temperature": settings.TEMPERATURE,
    }
    
    # Pass explicit credentials if they are set (for local dev)
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        
    return ChatBedrockConverse(**kwargs)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def process_message(
    user_message: str,
    session_id: str,
    phone: str | None = None,
    language: str = "auto",
) -> ChatResponse:
    """Process a user message through the Healthians AI pipeline.

    Flow:
        1. Load session history
        2. Convert to LangChain message formats
        3. Bind @tools to LLM
        4. Invoke LLM
        5. Execute tool calls if any
        6. Let LLM generate final response
        7. Update session history
        8. Return ChatResponse
    """

    # 1. Load History
    history = await get_session(session_id)
    
    # 2. Convert DB history to LangChain messages
    messages = []
    
    # Base system prompt with overrides
    sys_prompt = SYSTEM_PROMPT
    if language == "hi":
        sys_prompt += "\n\n[LANGUAGE OVERRIDE: Respond in Hindi (Devanagari script). Keep medical terms in English.]"
    elif language == "en":
        sys_prompt += "\n\n[LANGUAGE OVERRIDE: Respond in English only.]"

    if phone:
        sys_prompt += f"\n\n[USER CONTEXT: Registered phone number is {phone}]"
        
    messages.append(SystemMessage(content=sys_prompt))

    for msg in history:
        # We stored structured data in DB. For LangChain context, we just append it to the content.
        content = msg["content"]
        if msg.get("data"):
            content += f"\n\n[Tool Data Context: {json.dumps(msg['data'], ensure_ascii=False)}]"
            
        if msg["role"] == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    # 3. Bind Tools
    llm = _get_llm()
    tools = [explain_report, book_appointment, fetch_reports, answer_faq, escalate_to_doctor]
    llm_with_tools = llm.bind_tools(tools)
    
    # 4. Initial LLM Invoke
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {e}", exc_info=True)
        return ChatResponse(
            reply="Sorry, something went wrong. Please try again.",
            intent="error",
            data=None,
            suggested_followups=[],
            session_id=session_id
        )
        
    final_reply = response.content
    intent = "general_chat"
    data = None
    
    # 5. Handle Tool Calls natively
    if response.tool_calls:
        # We take the first tool call
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        intent = tool_name
        
        # Execute the tool
        try:
            # Map tool name to the actual tool object
            tool_map = {t.name: t for t in tools}
            target_tool = tool_map[tool_name]
            
            # Execute it async
            tool_output = await target_tool.ainvoke(tool_args)
            data = tool_output
            
            # 6. Let the LLM generate the final response
            # Append the AIMessage with tool calls
            messages.append(response)
            
            # Append the ToolMessage
            messages.append(ToolMessage(
                tool_call_id=tool_call["id"],
                name=tool_name,
                content=json.dumps(tool_output, ensure_ascii=False)
            ))
            
            # Invoke again to get final conversational response
            final_response = llm_with_tools.invoke(messages)
            
            # Sometimes LangChain might return empty content if there are subsequent tool calls.
            # In our simple flow, we assume one pass is enough.
            final_reply = final_response.content if final_response.content else json.dumps(tool_output)
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            final_reply = "I tried to process your request but encountered an error. Please try again."
            intent = "error"

    # 7. Save back to our DB format
    await add_message(session_id, "user", user_message)
    await add_message(session_id, "assistant", final_reply, data)

    # Note: Because the standard LangChain format doesn't explicitly guarantee a "suggested_followups" 
    # JSON field without further structured output wrappers, we pass an empty list.
    return ChatResponse(
        reply=final_reply,
        intent=intent,
        data=data,
        suggested_followups=[],
        session_id=session_id
    )

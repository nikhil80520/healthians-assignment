"""
sessions.py — Chat Session Manager for Healthians AI (Async SQLAlchemy)
"""

import json
from sqlalchemy.future import select
from sqlalchemy import delete

from config import settings
from database import AsyncSessionLocal, Message

async def get_session(session_id: str) -> list[dict]:
    """Retrieve chat history for a given session ID."""
    async with AsyncSessionLocal() as db:
        # Get messages ordered by creation time
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.id.asc())
        )
        records = result.scalars().all()
        
        history = []
        for r in records:
            msg = {"role": r.role, "content": r.content}
            if r.data:
                try:
                    msg["data"] = json.loads(r.data)
                except json.JSONDecodeError:
                    pass
            history.append(msg)
            
        return history

async def add_message(session_id: str, role: str, content: str, data: dict | None = None) -> None:
    """Add a new message to the session history, enforcing the MAX_HISTORY limit."""
    async with AsyncSessionLocal() as db:
        # Enforce max history limit
        result = await db.execute(
            select(Message.id)
            .where(Message.session_id == session_id)
            .order_by(Message.id.asc())
        )
        msg_ids = [row for row in result.scalars().all()]
        
        if len(msg_ids) >= settings.MAX_HISTORY:
            # Delete oldest messages to make room
            trim_count = len(msg_ids) - settings.MAX_HISTORY + 1
            ids_to_delete = msg_ids[:trim_count]
            await db.execute(
                delete(Message)
                .where(Message.id.in_(ids_to_delete))
            )
            
        # Add new message
        data_str = json.dumps(data) if data else None
        new_msg = Message(session_id=session_id, role=role, content=content, data=data_str)
        db.add(new_msg)
        await db.commit()

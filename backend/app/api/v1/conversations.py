from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user
from app.core.database import db
from app.services.conversation_orchestrator import conversation_orchestrator
from app.schemas.api import ConversationCreate, ConversationMessage, MessageResponse, UserResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    cid = uuid4()
    now = datetime.now(timezone.utc)
    conv_data = {
        "id": cid,
        "user_id": payload.user_id or current_user.id,
        "status": "ACTIVE",
        "language": payload.language,
        "created_at": now
    }
    db.conversations[cid] = conv_data
    return {
        "status": "created",
        "conversation_id": cid,
        "created_at": now.isoformat()
    }

@router.post("/messages", response_model=MessageResponse)
async def send_message_general(
    message: ConversationMessage,
    current_user: UserResponse = Depends(get_current_user)
):
    return conversation_orchestrator.process_message(message, user_id=current_user.id)

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message_to_conversation(
    conversation_id: UUID,
    message: ConversationMessage,
    current_user: UserResponse = Depends(get_current_user)
):
    message.conversation_id = conversation_id
    return conversation_orchestrator.process_message(message, user_id=current_user.id)

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: UserResponse = Depends(get_current_user)
):
    if conversation_id not in db.conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )

    conv = db.conversations[conversation_id]
    messages = [m for m in db.messages if m["conversation_id"] == conversation_id]
    return {
        "conversation": conv,
        "messages": messages
    }

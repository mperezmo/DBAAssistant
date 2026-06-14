# backend/app/routes/chat.py
"""Rutas de chat con Claude (Sprint 3). Todas requieren autenticación."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.chat import ChatRequest, ChatResponse, ConversationSummary
from app.services import chat_repo, claude

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, user: User = Depends(get_current_user)):
    """Envía un mensaje a Claude y persiste la conversación."""
    if not claude.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claude no está configurado: falta ANTHROPIC_API_KEY en el .env",
        )

    conv_id = req.conversation_id
    if conv_id:
        history = chat_repo.get_history(conv_id, user.username)
    else:
        history = []
        conv_id = chat_repo.create_conversation(user.username, req.message[:50])

    try:
        reply = claude.generate_reply(history, req.message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al llamar a Claude: {exc}",
        )

    chat_repo.add_message(conv_id, "user", req.message)
    chat_repo.add_message(conv_id, "assistant", reply)
    return ChatResponse(conversation_id=conv_id, reply=reply)


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(user: User = Depends(get_current_user)):
    return [
        ConversationSummary(id=c["id"], title=c.get("title", ""))
        for c in chat_repo.list_conversations(user.username)
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    conv = chat_repo.get_conversation(conversation_id, user.username)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )
    return conv

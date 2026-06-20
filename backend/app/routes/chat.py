# backend/app/routes/chat.py
"""Rutas de chat con Claude (Sprint 3). Todas requieren autenticación."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.chat import ChatRequest, ChatResponse, ConversationSummary
from app.services import chat_repo, claude, connections_repo, context_repo, schema_repo

router = APIRouter(prefix="/chat", tags=["chat"])


def _grounding(connection_id: str | None, database: str | None) -> str | None:
    """Arma el contexto (esquema real + negocio) para que la IA sepa dónde buscar."""
    if not connection_id or not database:
        return None
    parts: list[str] = []
    try:
        engine = connections_repo.get_engine_for_db(connection_id, database)
        if engine is not None:
            summary = schema_repo.schema_summary(engine)
            if summary:
                parts.append("Esquema (tabla(columnas)):\n" + summary)
    except Exception:  # noqa: BLE001
        pass
    try:
        biz = context_repo.build_prompt_context(connection_id, database)
        if biz:
            parts.append("Contexto de negocio:\n" + biz)
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(parts) or None


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
        reply = claude.generate_reply(history, req.message, _grounding(req.connection_id, req.database))
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

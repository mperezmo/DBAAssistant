# backend/app/models/chat.py
"""Modelos Pydantic para el chat (Sprint 3)."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None  # None → crea una conversación nueva
    # Opcional: ancla el chat a una base → la IA usa su esquema + contexto de negocio
    connection_id: str | None = None
    database: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


class ConversationSummary(BaseModel):
    id: str
    title: str

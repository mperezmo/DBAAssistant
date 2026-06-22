# backend/app/models/chat.py
"""Modelos Pydantic para el chat (Sprint 3 · agente con datos en Sprint 9)."""
from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None  # None → crea una conversación nueva


class QueryResult(BaseModel):
    """Resultado de una consulta que el agente ejecutó para responder."""
    connection_id: str
    database: str
    connection_name: str | None = None
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    result: QueryResult | None = None  # tabla de resultados si el bot ejecutó una query


class ConversationSummary(BaseModel):
    id: str
    title: str

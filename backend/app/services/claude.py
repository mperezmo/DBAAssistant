# backend/app/services/claude.py
"""Integración con la API de Anthropic Claude (Sprint 3)."""
from anthropic import Anthropic

from app.config import get_settings

settings = get_settings()

# Prompt de sistema: define el rol de DBA Assistant (prompt engineering).
DBA_SYSTEM_PROMPT = (
    "Eres DBA Assistant, un asistente experto en administración de bases de datos "
    "(SQL Server, MongoDB y Redis). Ayudas a DBAs y desarrolladores a generar "
    "consultas SQL, analizar y optimizar rendimiento, explicar planes de ejecución "
    "e índices, y resolver dudas.\n"
    "Reglas:\n"
    "- Responde en español, claro y conciso.\n"
    "- Cuando generes SQL, usa bloques de código ```sql y explica brevemente qué hace.\n"
    "- Advierte SIEMPRE antes de operaciones destructivas (DELETE/UPDATE sin WHERE, "
    "DROP, TRUNCATE).\n"
    "- No inventes esquemas ni datos; si falta información, pídela."
)

_client: Anthropic | None = None


def is_configured() -> bool:
    """True si hay API key para hablar con Claude."""
    return bool(settings.anthropic_api_key)


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not is_configured():
            raise RuntimeError("ANTHROPIC_API_KEY no configurada")
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_reply(history: list[dict], user_message: str) -> str:
    """Genera la respuesta del asistente.

    Args:
        history: mensajes previos [{role: 'user'|'assistant', content: str}, ...]
        user_message: el mensaje nuevo del usuario.
    Returns:
        El texto de la respuesta del asistente.
    """
    client = _get_client()
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})

    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=DBA_SYSTEM_PROMPT,
        messages=messages,
    )
    return "".join(block.text for block in resp.content if block.type == "text")

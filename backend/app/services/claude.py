# backend/app/services/claude.py
"""Integración con la API de Anthropic Claude (Sprint 3 / 5 / 9)."""
import json
import re

from anthropic import Anthropic

from app.config import get_settings

settings = get_settings()

# Prompt para refinar contexto de negocio "en criollo" → profesional + mapeado
# al esquema real (Sprint 9). La IA devuelve JSON estructurado.
CONTEXT_REFINE_PROMPT = (
    "Sos un arquitecto de datos. Recibís notas INFORMALES ('en criollo') sobre el "
    "negocio y el esquema REAL de una base SQL Server. Tu tarea: dejar el contexto "
    "de negocio PROFESIONAL, claro y ESTRUCTURADO, para que un asistente IA sepa en "
    "qué tablas/columnas está cada dato.\n"
    "Devolvé EXCLUSIVAMENTE un JSON con esta forma exacta (sin markdown ni texto extra):\n"
    '{"description": "string", "rules": ["string"], '
    '"glossary": [{"term": "string", "definition": "string"}]}\n'
    "- Redactá en español profesional, conciso.\n"
    "- En el glosario, mapeá cada término del negocio a su significado TÉCNICO usando "
    "los nombres REALES de tablas/columnas del esquema (no inventes objetos que no "
    "existan). Cuando aplique, incluí la condición/SQL aproximada.\n"
    "- Las reglas: normalizadas y accionables."
)

# Prompt para generación de T-SQL (Sprint 5).
SQL_SYSTEM_PROMPT = (
    "Sos un generador de T-SQL para Microsoft SQL Server. A partir de un pedido en "
    "lenguaje natural, devolvé ÚNICAMENTE la consulta T-SQL, sin explicaciones ni "
    "bloques de código markdown. Usá los nombres de tablas/columnas del esquema si se "
    "proporciona; no inventes objetos inexistentes."
)


def _strip_fences(text: str) -> str:
    """Quita bloques markdown ```sql ... ``` si Claude los incluyera."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()

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


def generate_reply(history: list[dict], user_message: str, extra_context: str | None = None) -> str:
    """Genera la respuesta del asistente.

    Args:
        history: mensajes previos [{role: 'user'|'assistant', content: str}, ...]
        user_message: el mensaje nuevo del usuario.
        extra_context: contexto de la base seleccionada (esquema + negocio) para
            que el asistente sepa dónde está cada dato.
    """
    client = _get_client()
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})

    system = DBA_SYSTEM_PROMPT
    if extra_context:
        system += (
            "\n\nContexto de la base seleccionada (usalo para saber en qué tablas y "
            "columnas está cada dato y para traducir términos del negocio):\n"
            + extra_context
        )

    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def _parse_context_json(text: str) -> dict:
    raw = _strip_fences(text)
    try:
        data = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
    return {
        "description": str(data.get("description", "") or ""),
        "rules": [str(r) for r in (data.get("rules") or []) if str(r).strip()],
        "glossary": [
            {"term": str(g.get("term", "")), "definition": str(g.get("definition", ""))}
            for g in (data.get("glossary") or []) if g.get("term")
        ],
    }


def refine_business_context(raw: dict, schema_summary: str | None = None) -> dict:
    """Profesionaliza el contexto 'en criollo' y lo mapea al esquema real (Sprint 9)."""
    client = _get_client()
    rules = "\n".join(f"- {r}" for r in raw.get("rules", []))
    glossary = "\n".join(f"- {g.get('term', '')}: {g.get('definition', '')}" for g in raw.get("glossary", []))
    content = (
        f"Esquema real de la base (tabla(columnas)):\n{schema_summary or '(no disponible)'}\n\n"
        "Notas informales del usuario:\n"
        f"Descripción: {raw.get('description', '')}\n"
        f"Reglas:\n{rules}\n"
        f"Glosario:\n{glossary}"
    )
    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=max(settings.claude_max_tokens, 2000),
        system=CONTEXT_REFINE_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return _parse_context_json(text)


def generate_sql(prompt: str, schema_context: str | None = None) -> str:
    """Genera T-SQL a partir de lenguaje natural (Sprint 5)."""
    client = _get_client()
    content = prompt
    if schema_context:
        content = f"Tablas disponibles: {schema_context}\n\nPedido: {prompt}"
    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=SQL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return _strip_fences(text)

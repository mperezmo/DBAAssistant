# backend/app/routes/chat.py
"""Chat-agente con Claude (Sprint 3/9). Autenticación requerida.

El agente elige solo a qué conexión/base ir (según el contexto de negocio del
catálogo), genera el SELECT, lo ejecuta (solo lectura, TOP 1000) y devuelve la
tabla de resultados además del texto.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.chat import ChatRequest, ChatResponse, ConversationSummary, QueryResult
from app.services import (
    audit_repo, chat_repo, claude, connections_repo, context_repo,
    query_history_repo, schema_repo, sql_executor, sql_validator,
)

router = APIRouter(prefix="/chat", tags=["chat"])

_MAX_CONNECTIONS = 10
_MAX_DBS = 10


def _build_catalog() -> tuple[str, dict[str, str]]:
    """Arma el catálogo (texto para la IA) y un mapa connection_id→name."""
    blocks: list[str] = []
    names: dict[str, str] = {}
    try:
        conns = connections_repo.list_all()
    except Exception:  # noqa: BLE001
        return "", names
    for c in conns[:_MAX_CONNECTIONS]:
        names[c["id"]] = c["name"]
        try:
            dbs = connections_repo.list_databases(c["id"]) or []
        except Exception:  # noqa: BLE001
            dbs = []
        for db in dbs[:_MAX_DBS]:
            block = f"### Conexión «{c['name']}» (connection_id={c['id']}) · base «{db}»\n"
            try:
                biz = context_repo.build_prompt_context(c["id"], db)
                if biz:
                    block += f"Contexto de negocio:\n{biz}\n"
            except Exception:  # noqa: BLE001
                pass
            try:
                engine = connections_repo.get_engine_for_db(c["id"], db)
                if engine is not None:
                    summary = schema_repo.schema_summary(engine)
                    if summary:
                        block += f"Esquema (tabla(columnas)):\n{summary}\n"
            except Exception:  # noqa: BLE001
                pass
            blocks.append(block)
    return "\n".join(blocks), names


def _make_runner(actor: str, names: dict[str, str]):
    """Callback que ejecuta el SELECT pedido por el agente (solo lectura)."""
    def run_query(args: dict) -> dict:
        cid = (args or {}).get("connection_id")
        db = (args or {}).get("database")
        sql = (args or {}).get("sql", "")
        if not sql_validator.is_read_only(sql):
            return {"error": "Solo se permiten consultas SELECT de solo lectura."}
        try:
            engine = connections_repo.get_engine_for_db(cid, db)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"No se pudo conectar: {exc}"}
        if engine is None:
            return {"error": "Conexión o base no encontrada."}
        try:
            columns, rows, truncated = sql_executor.run_select(engine, sql, 1000)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Error al ejecutar: {exc}"}
        query_history_repo.add(actor, cid, db, sql, kind="select", committed=False)
        audit_repo.log(actor, "chat.query", target=f"{cid}/{db}", detail=sql[:150])
        return {
            "connection_id": cid, "database": db, "connection_name": names.get(cid),
            "sql": sql, "columns": columns, "rows": rows,
            "row_count": len(rows), "truncated": truncated, "error": None,
        }
    return run_query


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, user: User = Depends(get_current_user)):
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

    actor = user.email or user.username
    catalog, names = _build_catalog()
    try:
        reply, captured = claude.chat_agent(history, req.message, catalog, _make_runner(actor, names))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error al llamar a Claude: {exc}")

    chat_repo.add_message(conv_id, "user", req.message)
    chat_repo.add_message(conv_id, "assistant", reply)
    result = QueryResult(**captured) if captured else None
    return ChatResponse(conversation_id=conv_id, reply=reply, result=result)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return conv

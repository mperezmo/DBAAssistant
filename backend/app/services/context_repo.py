# backend/app/services/context_repo.py
"""Contexto de negocio en MongoDB (Sprint 9).

Por conexión+base: descripción, reglas operativas y glosario; y por tabla:
alias de negocio, descripción, tags y marca de sensibilidad. Este contexto se
inyecta en los prompts de la IA (generación de SQL) para mejorar la precisión.
"""
from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["business_context"]

_TABLE_FIELDS = {
    "business_name": "", "description": "", "tags": [],
    "sensitive": False, "sensitive_columns": "", "restriction": "",
}


def get_db_context(connection_id: str, database: str) -> dict:
    doc = _col.find_one({"connection_id": connection_id, "database": database, "scope": "db"})
    if not doc:
        return {"description": "", "rules": [], "glossary": []}
    return {
        "description": doc.get("description", ""),
        "rules": doc.get("rules", []),
        "glossary": doc.get("glossary", []),
    }


def set_db_context(connection_id: str, database: str, data: dict) -> None:
    _col.update_one(
        {"connection_id": connection_id, "database": database, "scope": "db"},
        {"$set": {**data, "connection_id": connection_id, "database": database, "scope": "db"}},
        upsert=True,
    )


def get_table_context(connection_id: str, database: str, schema: str, table: str) -> dict:
    doc = _col.find_one({
        "connection_id": connection_id, "database": database, "scope": "table",
        "schema_name": schema, "table_name": table,
    })
    if not doc:
        return dict(_TABLE_FIELDS)
    return {k: doc.get(k, default) for k, default in _TABLE_FIELDS.items()}


def set_table_context(connection_id: str, database: str, schema: str, table: str, data: dict) -> None:
    _col.update_one(
        {"connection_id": connection_id, "database": database, "scope": "table",
         "schema_name": schema, "table_name": table},
        {"$set": {**data, "connection_id": connection_id, "database": database, "scope": "table",
                  "schema_name": schema, "table_name": table}},
        upsert=True,
    )


def list_table_contexts(connection_id: str, database: str) -> list[dict]:
    docs = _col.find({"connection_id": connection_id, "database": database, "scope": "table"})
    out = []
    for d in docs:
        entry = {k: d.get(k, default) for k, default in _TABLE_FIELDS.items()}
        entry["schema_name"] = d["schema_name"]
        entry["table_name"] = d["table_name"]
        out.append(entry)
    return out


def build_prompt_context(connection_id: str, database: str) -> str:
    """Arma un bloque de texto con el contexto de negocio para la IA."""
    parts: list[str] = []
    dbc = get_db_context(connection_id, database)
    if dbc["description"]:
        parts.append(f"Descripción de la base: {dbc['description']}")
    if dbc["rules"]:
        parts.append("Reglas operativas:\n- " + "\n- ".join(dbc["rules"]))
    if dbc["glossary"]:
        parts.append("Glosario:\n" + "\n".join(
            f"- {g['term']}: {g.get('definition', '')}" for g in dbc["glossary"]
        ))
    tables = list_table_contexts(connection_id, database)
    lines = []
    for t in tables:
        bits = []
        if t["business_name"]:
            bits.append(f"alias de negocio '{t['business_name']}'")
        if t["description"]:
            bits.append(t["description"])
        if t["sensitive"]:
            bits.append(f"SENSIBLE ({t['restriction'] or 'acceso restringido'})")
        if bits:
            lines.append(f"- {t['schema_name']}.{t['table_name']}: " + "; ".join(bits))
    if lines:
        parts.append("Notas de tablas:\n" + "\n".join(lines))
    return "\n\n".join(parts)

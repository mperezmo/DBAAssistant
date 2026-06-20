# tests/unit/test_context.py
"""Tests del contexto de negocio (Sprint 9). context_repo mockeado."""
from unittest.mock import patch

CONN = "650000000000000000000001"
DB = "MXApp"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_context_requires_auth(client):
    assert client.get(f"/context/{CONN}/{DB}").status_code == 401


def test_read_db_context(client):
    token = _token(client)
    fake = {"description": "ERP", "rules": ["r1"], "glossary": [{"term": "t", "definition": "d"}]}
    with patch("app.services.context_repo.get_db_context", return_value=fake):
        res = client.get(f"/context/{CONN}/{DB}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["description"] == "ERP"


def test_write_db_context_audits(client):
    token = _token(client)
    body = {"description": "ERP de ventas", "rules": ["No exponer sueldos"], "glossary": []}
    with patch("app.services.context_repo.set_db_context") as mock_set, \
         patch("app.services.cache.invalidate_connection"), \
         patch("app.services.audit_repo.log") as mock_log:
        res = client.put(f"/context/{CONN}/{DB}", json=body, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    mock_set.assert_called_once()
    assert mock_log.call_args.args[1] == "context.update"


def test_write_table_context(client):
    token = _token(client)
    body = {"business_name": "Clientes", "description": "maestro", "tags": ["core"],
            "sensitive": True, "sensitive_columns": "email", "restriction": "enmascaramiento"}
    with patch("app.services.context_repo.set_table_context") as mock_set, \
         patch("app.services.audit_repo.log"):
        res = client.put(f"/context/{CONN}/{DB}/tables/dbo/clientes", json=body,
                         headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["business_name"] == "Clientes"
    mock_set.assert_called_once()


def test_build_prompt_context_format():
    # unit puro del armado del prompt (con repo mockeado a nivel de funciones internas)
    from app.services import context_repo
    with patch.object(context_repo, "get_db_context", return_value={
            "description": "ERP", "rules": ["regla1"], "glossary": [{"term": "x", "definition": "y"}]}), \
         patch.object(context_repo, "list_table_contexts", return_value=[
            {"schema_name": "dbo", "table_name": "clientes", "business_name": "Clientes",
             "description": "", "tags": [], "sensitive": True, "sensitive_columns": "", "restriction": "mask"}]):
        text = context_repo.build_prompt_context(CONN, DB)
    assert "ERP" in text and "regla1" in text and "Clientes" in text and "SENSIBLE" in text


def test_refine_without_api_key(client):
    token = _token(client)
    with patch("app.services.claude.is_configured", return_value=False):
        res = client.post(f"/context/{CONN}/{DB}/refine",
                          json={"description": "x", "rules": [], "glossary": []},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 503


def test_refine_ok(client):
    token = _token(client)
    refined = {"description": "ERP profesional", "rules": ["R1"],
               "glossary": [{"term": "cliente activo", "definition": "clientes WHERE estado=1"}]}
    with patch("app.services.claude.is_configured", return_value=True), \
         patch("app.services.connections_repo.get_engine_for_db", return_value=None), \
         patch("app.services.claude.refine_business_context", return_value=refined):
        res = client.post(f"/context/{CONN}/{DB}/refine",
                          json={"description": "erp de ventas", "rules": ["r"], "glossary": []},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["description"] == "ERP profesional"
    assert res.json()["glossary"][0]["term"] == "cliente activo"

# tests/unit/test_chat.py
"""Tests del chat-agente (Sprint 3/9). Claude y repos mockeados."""
from unittest.mock import patch


def _token(client, username="admin", password="admin123"):
    res = client.post("/auth/login", data={"username": username, "password": password})
    return res.json()["access_token"]


def test_chat_requires_auth(client):
    res = client.post("/chat", json={"message": "hola"})
    assert res.status_code == 401


def test_chat_without_api_key_returns_503(client):
    token = _token(client)
    with patch("app.services.claude.is_configured", return_value=False):
        res = client.post("/chat", json={"message": "hola"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 503


def test_chat_returns_reply(client):
    token = _token(client)
    with patch("app.services.claude.is_configured", return_value=True), \
         patch("app.services.claude.chat_agent", return_value=("Hola, soy el asistente.", None)), \
         patch("app.services.chat_repo.create_conversation", return_value="conv123"), \
         patch("app.services.chat_repo.add_message"), \
         patch("app.services.chat_repo.get_history", return_value=[]):
        res = client.post("/chat", json={"message": "hola"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["reply"].startswith("Hola")
    assert body["conversation_id"] == "conv123"
    assert body["result"] is None


def test_chat_returns_query_result(client):
    token = _token(client)
    captured = {
        "connection_id": "X", "database": "DB", "connection_name": "Local",
        "sql": "SELECT TOP 1000 * FROM clientes",
        "columns": ["id", "nombre"], "rows": [[1, "Marina"]],
        "row_count": 1, "truncated": False,
    }
    with patch("app.services.claude.is_configured", return_value=True), \
         patch("app.services.claude.chat_agent", return_value=("Hay 1 cliente.", captured)), \
         patch("app.services.chat_repo.create_conversation", return_value="c1"), \
         patch("app.services.chat_repo.add_message"), \
         patch("app.services.chat_repo.get_history", return_value=[]):
        res = client.post("/chat", json={"message": "dame los clientes"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["result"]["columns"] == ["id", "nombre"]
    assert body["result"]["truncated"] is False
    assert body["result"]["connection_name"] == "Local"


def test_list_conversations_requires_auth(client):
    res = client.get("/chat/conversations")
    assert res.status_code == 401

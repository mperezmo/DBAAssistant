# tests/unit/test_chat.py
"""Tests del chat (Sprint 3). Claude y MongoDB se mockean: no se hacen llamadas reales."""
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
        res = client.post(
            "/chat",
            json={"message": "hola"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 503


def test_chat_returns_reply(client):
    token = _token(client)
    with patch("app.services.claude.is_configured", return_value=True), \
         patch("app.services.claude.generate_reply", return_value="SELECT 1;"), \
         patch("app.services.chat_repo.create_conversation", return_value="conv123"), \
         patch("app.services.chat_repo.add_message", return_value=None), \
         patch("app.services.chat_repo.get_history", return_value=[]):
        res = client.post(
            "/chat",
            json={"message": "dame un select"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["reply"] == "SELECT 1;"
    assert body["conversation_id"] == "conv123"


def test_list_conversations_requires_auth(client):
    res = client.get("/chat/conversations")
    assert res.status_code == 401

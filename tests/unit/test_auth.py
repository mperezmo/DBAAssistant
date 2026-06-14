# tests/unit/test_auth.py
"""Tests de autenticación (modo local)."""


def test_login_success(client):
    res = client.post(
        "/auth/login", data={"username": "admin", "password": "admin123"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    res = client.post(
        "/auth/login", data={"username": "admin", "password": "incorrecta"}
    )
    assert res.status_code == 401


def test_me_requires_auth(client):
    # Sin token → 401
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_with_valid_token(client):
    login = client.post(
        "/auth/login", data={"username": "dba", "password": "dba12345"}
    )
    token = login.json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "dba"
    assert "dba" in body["roles"]
    # El hash NUNCA debe exponerse
    assert "hashed_password" not in body


def test_me_with_invalid_token(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert res.status_code == 401

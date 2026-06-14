# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client():
    # Los tests fuerzan el modo de auth LOCAL para ser deterministas,
    # independientemente del AUTH_MODE del .env del desarrollador.
    settings = get_settings()
    original_mode = settings.auth_mode
    settings.auth_mode = "local"
    try:
        yield TestClient(app)
    finally:
        settings.auth_mode = original_mode

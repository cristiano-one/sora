"""Fixtures compartilhadas dos testes."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Cliente de teste reutilizável (fecha o app ao final)."""
    with TestClient(app) as test_client:
        yield test_client

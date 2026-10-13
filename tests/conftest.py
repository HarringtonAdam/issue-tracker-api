import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
import models


@pytest.fixture
def db_engine(tmp_path):
    """Give every test a fresh SQLite file, independent of tracker.db."""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(db_engine, monkeypatch):
    # main creates tables at import time: redirect that operation before importing it.
    # Importing database/models above creates no database connections.
    monkeypatch.setattr(database, "engine", db_engine)
    import main

    test_sessions = sessionmaker(bind=db_engine)

    def override_get_db():
        with test_sessions() as session:
            yield session

    monkeypatch.setitem(main.app.dependency_overrides, main.get_db, override_get_db)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def create_issue(client):
    """Create through the API, with valid defaults and optional field overrides."""
    def create(**overrides):
        payload = {
            "title": "Fix login page",
            "description": "Users cannot sign in.",
            "priority": "medium",
        }
        payload.update(overrides)
        response = client.post("/issues", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create

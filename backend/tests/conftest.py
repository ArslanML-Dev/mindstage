import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/mindstage_test")
os.environ["GEMINI_API_KEY"] = ""  # tests always use demo mode: no network, no cost

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

NOTES = ("Photosynthesis is how green plants make food. Chlorophyll in chloroplasts captures sunlight. "
         "Plants take in carbon dioxide through stomata and water through roots. They produce glucose and "
         "release oxygen. The rate rises with light intensity until carbon dioxide becomes limiting.")


@pytest.fixture(scope="session", autouse=True)
def migrated():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE classrooms RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def classroom(client):
    r = client.post("/api/classrooms", json={"title": "Biology 9A"})
    assert r.status_code == 201
    return r.json()

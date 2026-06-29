import os
import tempfile

import pytest

# DB sementara (file, bukan in-memory) supaya background task thread lain ikut lihat.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.name}"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    init_db()
    yield
    try:
        os.unlink(_TMP.name)
    except OSError:
        pass


@pytest.fixture()
def client():
    return TestClient(app)


import uuid  # noqa: E402


@pytest.fixture()
def auth_headers(client):
    uid = uuid.uuid4().hex[:8]
    r = client.post("/auth/register", json={
        "handle": f"trader_{uid}", "email": f"{uid}@example.com", "password": "secret123",
    })
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

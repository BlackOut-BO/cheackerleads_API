import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BUYING_DB", str(tmp_path / "buying.db"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("KAITEN_API_KEY", "test")
    import importlib

    legacy = None
    if (ROOT / "app" / "celebs").exists():  # в репозитории отдельного проекта пакета может не быть
        from app.celebs import store
        importlib.reload(store)
        from app.celebs import legacy
        monkeypatch.setattr(legacy.db, "DB_PATH", tmp_path / "bot.db")
        from app.celebs import service, router, project
        importlib.reload(service)
        importlib.reload(router)
        importlib.reload(project)
    if (ROOT / "app" / "leads").exists():
        from app.leads import store as leads_store
        monkeypatch.setattr(leads_store, "DB_PATH", tmp_path / "buying.db")
    from app import main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        c.legacy = legacy
        yield c


def wait(client, sid, user=None, timeout=5):
    h = {"X-User-Id": str(user)} if user else {}
    end = time.time() + timeout
    while time.time() < end:
        s = client.get(f"/api/buying/celebs/searches/{sid}", headers=h).json()
        if s["status"] in ("done", "error", "cancelled"):
            return s
        time.sleep(0.05)
    raise AssertionError(f"search {sid} not finished: {s['status']}")

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


class DummyDb:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture()
def dummy_db() -> DummyDb:
    return DummyDb()


@pytest.fixture()
def client(dummy_db: DummyDb) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

import pytest
from fastapi.testclient import TestClient

from app.lender import LenderClient
from app.main import api
from app.store import ApplicationStore


@pytest.fixture
def lender() -> LenderClient:
    return LenderClient()


@pytest.fixture
def client(lender):
    api.state.store = ApplicationStore()
    api.state.lender = lender
    return TestClient(api)


@pytest.fixture
def new_application(client):
    def _create(**overrides) -> dict:
        body = {"business_name": "Blue Door Bakery", "requested_amount": 50_000, "lender": "acme-capital"}
        body.update(overrides)
        resp = client.post("/applications", json=body)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create

import hashlib
import hmac

import pytest

# Task 2 (stretch): delete the next line when you start on the webhook.
pytestmark = pytest.mark.skip(reason="Task 2 (stretch) not started")

SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    monkeypatch.setenv("LENDER_WEBHOOK_SECRET", SECRET)


def sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def submitted_application(client, new_application):
    app = new_application()
    return client.post(f"/applications/{app['id']}/submit").json()


def event(reference: str, status: str, event_id: str = "evt_001") -> bytes:
    # Byte-for-byte what the lender sends.
    return (
        '{"event_id":  "%s", "lender_reference": "%s", "status": "%s"}' % (event_id, reference, status)
    ).encode()


def post_event(client, body: bytes, signature: str | None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Lender-Signature"] = signature
    return client.post("/webhooks/lender-status", content=body, headers=headers)


def test_valid_event_updates_status(client, submitted_application):
    body = event(submitted_application["lender_reference"], "approved")

    resp = post_event(client, body, sign(body))

    assert resp.status_code == 200
    assert client.get(f"/applications/{submitted_application['id']}").json()["status"] == "approved"


def test_missing_signature_is_rejected(client, submitted_application):
    body = event(submitted_application["lender_reference"], "approved")

    assert post_event(client, body, None).status_code == 401


def test_wrong_secret_is_rejected(client, submitted_application):
    body = event(submitted_application["lender_reference"], "approved")

    assert post_event(client, body, sign(body, "not-the-secret")).status_code == 401


def test_tampered_body_is_rejected(client, submitted_application):
    body = event(submitted_application["lender_reference"], "approved")
    tampered = event(submitted_application["lender_reference"], "funded")

    resp = post_event(client, tampered, sign(body))

    assert resp.status_code == 401
    assert client.get(f"/applications/{submitted_application['id']}").json()["status"] == "submitted"


def test_unknown_reference_is_404(client, submitted_application):
    body = event("LND-99999", "approved")

    assert post_event(client, body, sign(body)).status_code == 404

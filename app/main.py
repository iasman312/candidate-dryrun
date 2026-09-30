import logging
import hashlib
import hmac
import json
import os

from fastapi import Depends, FastAPI, HTTPException, Request

from app.lender import LenderClient
from app.models import Application, ApplicationIn, Status
from app.service import InvalidState, SubmissionFailed, submit_application
from app.store import ApplicationStore

logger = logging.getLogger(__name__)

# Allowed lender-driven transitions.
NEXT_STATUSES = {
    Status.SUBMITTED: {Status.APPROVED, Status.DECLINED},
    Status.APPROVED: {Status.FUNDED, Status.DECLINED},
}

api = FastAPI(title="Lender Submissions")
api.state.store = ApplicationStore()
api.state.lender = LenderClient()


def get_store() -> ApplicationStore:
    return api.state.store


def get_lender() -> LenderClient:
    return api.state.lender


@api.post("/applications", status_code=201)
def create_application(data: ApplicationIn, store: ApplicationStore = Depends(get_store)) -> Application:
    return store.create(data)


@api.get("/applications")
def list_applications(status: Status | None = None, store: ApplicationStore = Depends(get_store)) -> list[Application]:
    return store.list(status=status)


@api.get("/applications/{app_id}")
def get_application(app_id: str, store: ApplicationStore = Depends(get_store)) -> Application:
    app = store.get(app_id)
    if app is None:
        raise HTTPException(404, "application not found")
    return app


@api.post("/applications/{app_id}/submit")
def submit(
    app_id: str,
    store: ApplicationStore = Depends(get_store),
    lender: LenderClient = Depends(get_lender),
) -> Application:
    app = store.get(app_id)
    if app is None:
        raise HTTPException(404, "application not found")
    try:
        return submit_application(app, lender)
    except InvalidState as exc:
        raise HTTPException(409, str(exc))
    except SubmissionFailed as exc:
        raise HTTPException(502, str(exc))


@api.post("/webhooks/lender-status")
async def lender_status_webhook(request: Request, store: ApplicationStore = Depends(get_store)):
    # Sign-check the raw bytes: re-serializing the JSON would change them.
    body = await request.body()
    secret = os.environ["LENDER_WEBHOOK_SECRET"].encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Lender-Signature", "")):
        raise HTTPException(401, "invalid signature")

    try:
        event = json.loads(body)
        status = Status(event["status"])
        event_id, reference = event["event_id"], event["lender_reference"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(422, "malformed event")
    if status not in NEXT_STATUSES[Status.SUBMITTED] | NEXT_STATUSES[Status.APPROVED]:
        raise HTTPException(422, f"unexpected status {status.value}")

    app = store.find_by_lender_reference(reference)
    if app is None:
        raise HTTPException(404, "unknown lender reference")

    # Duplicates and stale (out-of-order) events are acknowledged with 200 so the lender stops
    # retrying, but they never move an application backwards.
    if event_id in app.processed_event_ids:
        return {"result": "duplicate"}
    app.processed_event_ids.add(event_id)
    if status not in NEXT_STATUSES.get(app.status, set()):
        logger.info("ignoring %s for %s: already %s", status.value, app.id, app.status.value)
        return {"result": "ignored"}
    app.status = status
    return {"result": "updated"}

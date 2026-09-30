import logging

from app.lender import LenderClient, LenderTimeout, LenderUnreachable
from app.models import Application, Status

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


class SubmissionFailed(Exception):
    pass


class InvalidState(Exception):
    pass


def submit_application(app: Application, lender: LenderClient) -> Application:
    if app.status != Status.DRAFT:
        raise InvalidState(f"application {app.id} is already {app.status.value}")

    # A timeout doesn't tell us whether the lender recorded the submission, so every retry must
    # carry the same idempotency key. The application id is stable across retries and restarts.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reference = lender.submit(app, idempotency_key=app.id)
            break
        except (LenderUnreachable, LenderTimeout) as exc:
            logger.warning("lender submit failed (attempt %d/%d): %r", attempt, MAX_ATTEMPTS, exc)
    else:
        raise SubmissionFailed(f"lender did not accept application {app.id}")

    app.lender_reference = reference
    app.status = Status.SUBMITTED
    return app

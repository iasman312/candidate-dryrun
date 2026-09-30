"""Client for the lender's submission API.

This is a fake: instead of making HTTP calls it records submissions in memory,
so tests can see exactly what the lender received.
"""

from app.models import Application


class LenderUnreachable(Exception):
    """The request never reached the lender (DNS failure, connection refused)."""


class LenderTimeout(Exception):
    """We sent the request but got no response in time.

    The lender may or may not have received and recorded the submission.
    """


class LenderClient:
    def __init__(self) -> None:
        # Every submission the lender has recorded, in order.
        self.submissions: list[dict] = []
        self._by_idempotency_key: dict[str, str] = {}

    def submit(self, application: Application, idempotency_key: str | None = None) -> str:
        """Submit an application and return the lender's reference id.

        If `idempotency_key` is given and the lender has already seen it, the lender
        returns the original reference instead of recording a new submission.
        """
        if idempotency_key and idempotency_key in self._by_idempotency_key:
            return self._by_idempotency_key[idempotency_key]

        reference = f"LND-{len(self.submissions) + 1:05d}"
        self.submissions.append(
            {
                "reference": reference,
                "business_name": application.business_name,
                "requested_amount": application.requested_amount,
            }
        )
        if idempotency_key:
            self._by_idempotency_key[idempotency_key] = reference
        return reference

import pytest

from app.lender import LenderClient, LenderTimeout, LenderUnreachable


class UnreachableAtFirst(LenderClient):
    """Connection refused for the first N calls; the lender never sees them."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures_left = failures

    def submit(self, application, idempotency_key=None):
        if self.failures_left:
            self.failures_left -= 1
            raise LenderUnreachable("connection refused")
        return super().submit(application, idempotency_key)


class TimesOutAfterRecording(LenderClient):
    """The lender records the submission, but the response is lost for the first N calls."""

    def __init__(self, timeouts: int) -> None:
        super().__init__()
        self.timeouts_left = timeouts

    def submit(self, application, idempotency_key=None):
        reference = super().submit(application, idempotency_key)
        if self.timeouts_left:
            self.timeouts_left -= 1
            raise LenderTimeout("read timed out")
        return reference


def test_submit_marks_application_submitted(client, lender, new_application):
    app = new_application()

    resp = client.post(f"/applications/{app['id']}/submit")

    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"
    assert resp.json()["lender_reference"] == lender.submissions[0]["reference"]


def test_cannot_submit_twice(client, lender, new_application):
    app = new_application()
    client.post(f"/applications/{app['id']}/submit")

    resp = client.post(f"/applications/{app['id']}/submit")

    assert resp.status_code == 409
    assert len(lender.submissions) == 1


@pytest.mark.parametrize("lender", [UnreachableAtFirst(failures=2)])
def test_retries_when_lender_briefly_unreachable(client, lender, new_application):
    app = new_application()

    resp = client.post(f"/applications/{app['id']}/submit")

    assert resp.status_code == 200
    assert len(lender.submissions) == 1


@pytest.mark.parametrize("lender", [UnreachableAtFirst(failures=10)])
def test_gives_up_after_repeated_failures(client, lender, new_application):
    app = new_application()

    resp = client.post(f"/applications/{app['id']}/submit")

    assert resp.status_code == 502
    assert client.get(f"/applications/{app['id']}").json()["status"] == "draft"


@pytest.mark.parametrize("lender", [TimesOutAfterRecording(timeouts=2)])
def test_timeouts_do_not_create_duplicate_submissions(client, lender, new_application):
    app = new_application()

    resp = client.post(f"/applications/{app['id']}/submit")

    assert resp.status_code == 200
    assert len(lender.submissions) == 1
    assert resp.json()["lender_reference"] == lender.submissions[0]["reference"]

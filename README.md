# Lender Submissions: live exercise

A small FastAPI service that takes business funding applications and submits them to a lender.
It's a simplified version of the kind of service you'd work on with us. Storage and the lender API are
faked in memory, so there is nothing to install beyond Python.

**Time: about 25 minutes.** We care more about how you work than how fast you finish.

## Ground rules

- **Use any AI tools you normally use** (Claude, Cursor, Copilot, ChatGPT, anything). We want to see how
  you work with them.
- **Think out loud.** Tell us what you're checking, what you believe, and why you accept or reject what
  the AI suggests.
- **Ask questions.** If a requirement is unclear, ask us, just as you would ask a teammate.
- Work in your own copy (**Use this template → Create a new repository**, under your own account), then
  open a pull request **in your copy** from a branch to `main`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                       # one test fails right now, which is expected
uvicorn app.main:api --reload   # optional: http://127.0.0.1:8000/docs
```

Python 3.11 or newer.

## Layout

```
app/main.py      HTTP endpoints
app/service.py   submission logic (retries)
app/lender.py    the lender API client (fake)
app/store.py     in-memory storage
app/models.py    data models
tests/           pytest suite
```

## Task 1: bug report from the lender (main task)

> "We're getting the same application from you two or three times. It mostly happens when our API is
> slow. Please stop. Duplicates create real problems on our side."

Find the cause, fix it, and open a pull request. `pytest -q` currently has one failing test, which
reproduces the report. Making it pass is the start, not the finish: be ready to explain why your fix is
correct.

## Task 2: lender status webhook (stretch, only if you have time)

The lender will call us when a decision is made. Implement `POST /webhooks/lender-status`.

- Request body (JSON):
  ```json
  {"event_id": "evt_001", "lender_reference": "LND-00001", "status": "approved"}
  ```
  `status` is one of `approved`, `declined`, `funded`.
- **Authentication:** the lender sends an `X-Lender-Signature` header containing the hex-encoded
  HMAC-SHA256 of the request body, signed with a shared secret. Read the secret from the
  `LENDER_WEBHOOK_SECRET` environment variable.
- Respond with:
  - `401` if the signature is missing or invalid
  - `404` if `lender_reference` doesn't match an application
  - `200` after updating the application's status
- Lenders sometimes send the same event more than once, and events can arrive out of order.
  Handle this sensibly.

Tests are in `tests/test_webhook.py`. They're skipped until you remove the `pytestmark` line at the top.

## When you're done

Open the PR in your copy. In the description, include what you changed and why, what you'd do next with
more time, and anything you noticed that we didn't ask about.

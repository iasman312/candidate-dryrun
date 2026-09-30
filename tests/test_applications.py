def test_create_and_get(client, new_application):
    created = new_application()
    assert created["status"] == "draft"

    resp = client.get(f"/applications/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == created


def test_get_unknown_application_is_404(client):
    assert client.get("/applications/does-not-exist").status_code == 404


def test_rejects_non_positive_amount(client):
    resp = client.post(
        "/applications",
        json={"business_name": "Blue Door Bakery", "requested_amount": 0, "lender": "acme-capital"},
    )
    assert resp.status_code == 422


def test_list_returns_oldest_first(client, new_application):
    first = new_application(business_name="First")
    second = new_application(business_name="Second")

    ids = [a["id"] for a in client.get("/applications").json()]
    assert ids == [first["id"], second["id"]]


def test_filter_by_status(client, new_application):
    draft = new_application(business_name="Still a draft")
    submitted = new_application(business_name="Sent to lender")
    client.post(f"/applications/{submitted['id']}/submit")

    resp = client.get("/applications", params={"status": "submitted"})
    assert [a["id"] for a in resp.json()] == [submitted["id"]]

    resp = client.get("/applications", params={"status": "draft"})
    assert [a["id"] for a in resp.json()] == [draft["id"]]


def test_filter_rejects_unknown_status(client):
    assert client.get("/applications", params={"status": "bogus"}).status_code == 422

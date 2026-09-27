from tests.test_clients import auth_header, create_client
from tests.test_contracts import create_service


def setup_billable_client(client, headers, cleanings=12):
    """Client with a contract (fee 100, cleaning 40) and activities in Sept."""
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]
    client.put(f"/api/clients/{client_id}/contract", json={
        "fixed_monthly_fee": "100",
        "prices": [{"service_id": service_id, "unit_price": 40}],
    }, headers=headers)
    for day in range(1, cleanings + 1):
        client.post("/api/activities", json={
            "client_id": client_id, "service_id": service_id,
            "performed_on": f"2026-09-{day:02d}", "quantity": 1,
        }, headers=headers)
    return client_id, service_id


def test_close_month_creates_proposals_with_totals(client):
    headers = auth_header(client)
    client_id, service_id = setup_billable_client(client, headers)
    client.post("/api/activities", json={
        "client_id": client_id, "service_id": service_id,
        "performed_on": "2026-10-01", "quantity": 1,
    }, headers=headers)

    response = client.post("/api/billing-runs", json={"month": "2026-09"},
                           headers=headers)
    assert response.status_code == 201
    run = response.get_json()
    assert run["year"] == 2026 and run["month"] == 9
    assert run["status"] == "open"
    assert len(run["proposals"]) == 1

    proposal = run["proposals"][0]
    assert proposal["client_id"] == client_id
    assert proposal["status"] == "draft"
    assert proposal["subtotal"] == "580.00"
    assert proposal["vat_amount"] == "121.80"
    assert proposal["total"] == "701.80"
    assert [line["description"] for line in proposal["lines"]] == [
        "Cuota fija mensual", "Limpieza de oficina"]
    assert len(proposal["lines"][1]["activity_ids"]) == 12

    september = client.get("/api/activities?month=2026-09",
                           headers=headers).get_json()
    assert all(a["proposal_line_id"] is not None for a in september)
    october = client.get("/api/activities?month=2026-10",
                         headers=headers).get_json()
    assert october[0]["proposal_line_id"] is None


def test_close_month_twice_is_rejected(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)

    first = client.post("/api/billing-runs", json={"month": "2026-09"},
                        headers=headers)
    second = client.post("/api/billing-runs", json={"month": "2026-09"},
                         headers=headers)
    assert first.status_code == 201
    assert second.status_code == 409


def test_close_month_rejects_bad_month(client):
    headers = auth_header(client)

    for month in ("septiembre", "2026-13", "09-2026", None):
        response = client.post("/api/billing-runs", json={"month": month},
                               headers=headers)
        assert response.status_code == 400


def test_clients_with_nothing_to_bill_get_no_proposal(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a)
    create_client(client, headers_a, name="Cliente sin contrato")

    run_a = client.post("/api/billing-runs", json={"month": "2026-09"},
                        headers=headers_a).get_json()
    run_b = client.post("/api/billing-runs", json={"month": "2026-09"},
                        headers=headers_b).get_json()
    assert len(run_a["proposals"]) == 1
    assert run_b["proposals"] == []


def test_list_and_get_billing_runs(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)
    run_id = client.post("/api/billing-runs", json={"month": "2026-09"},
                         headers=headers).get_json()["id"]
    client.post("/api/billing-runs", json={"month": "2026-10"},
                headers=headers)

    response = client.get("/api/billing-runs", headers=headers)
    assert response.status_code == 200
    assert [(r["year"], r["month"]) for r in response.get_json()] == [
        (2026, 10), (2026, 9)]

    response = client.get(f"/api/billing-runs/{run_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["proposals"][0]["total"] == "701.80"


def test_billing_run_of_other_tenant_is_not_found(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    run_id = client.post("/api/billing-runs", json={"month": "2026-09"},
                         headers=headers_a).get_json()["id"]

    assert client.get(f"/api/billing-runs/{run_id}",
                      headers=headers_b).status_code == 404
    assert client.get("/api/billing-runs", headers=headers_b).get_json() == []

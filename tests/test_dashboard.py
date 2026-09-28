from tests.test_billing_runs import setup_billable_client
from tests.test_clients import auth_header, create_client


def test_dashboard_counts_activities_and_proposals(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)
    url = "/api/dashboard?month=2026-09"

    response = client.get(url, headers=headers)
    assert response.mimetype == "application/json"
    assert response.status_code == 200
    body = response.get_json()
    assert body["month"] == "2026-09"
    assert body["active_clients"] == 1
    assert body["activities"] == {"total": 12, "unbilled": 12}
    assert body["billing_run"] is None
    assert body["proposals"] == {"draft": 0, "approved": 0}
    assert body["totals"] == {"draft": "0.00", "approved": "0.00"}
    assert body["clients_without_activity"] == []

    idle_id = create_client(
        client, headers, name="Cliente sin actividad")["id"]
    client.put(f"/api/clients/{idle_id}/contract",
               json={"fixed_monthly_fee": "0"}, headers=headers)
    body = client.get(url, headers=headers).get_json()
    assert body["active_clients"] == 2
    assert body["clients_without_activity"] == [
        {"client_id": idle_id, "client_name": "Cliente sin actividad"}]

    run = client.post("/api/billing-runs", json={"month": "2026-09"},
                      headers=headers).get_json()
    body = client.get(url, headers=headers).get_json()
    assert body["activities"] == {"total": 12, "unbilled": 0}
    assert body["billing_run"] == {"id": run["id"], "status": "open"}
    assert body["proposals"] == {"draft": 1, "approved": 0}
    assert body["totals"] == {"draft": "701.80", "approved": "0.00"}

    client.post(f"/api/proposals/{run['proposals'][0]['id']}/approve",
                headers=headers)
    body = client.get(url, headers=headers).get_json()
    assert body["billing_run"] == {"id": run["id"], "status": "closed"}
    assert body["proposals"] == {"draft": 0, "approved": 1}
    assert body["totals"] == {"draft": "0.00", "approved": "701.80"}


def test_dashboard_rejects_bad_month_and_is_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a)

    assert client.get("/api/dashboard?month=septiembre",
                      headers=headers_a).status_code == 400

    body = client.get("/api/dashboard?month=2026-09",
                      headers=headers_b).get_json()
    assert body["active_clients"] == 0
    assert body["activities"] == {"total": 0, "unbilled": 0}

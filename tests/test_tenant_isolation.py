"""A user of company B must never see, change or download data of company A."""
from tests.test_billing_runs import setup_billable_client
from tests.test_clients import auth_header


def _close_september(client, headers):
    run = client.post("/api/billing-runs", json={"month": "2026-09"},
                      headers=headers).get_json()
    return run["id"], run["proposals"][0]["id"]


def test_activities_of_another_tenant_are_invisible(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a, cleanings=3)

    response = client.get("/api/activities?month=2026-09", headers=headers_b)

    assert response.status_code == 200
    assert response.get_json() == []


def test_billing_run_of_another_tenant_is_not_found(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a, cleanings=3)
    run_id, _ = _close_september(client, headers_a)

    assert client.get(f"/api/billing-runs/{run_id}",
                      headers=headers_b).status_code == 404
    assert client.get(f"/api/billing-runs/{run_id}/export.csv",
                      headers=headers_b).status_code == 404
    assert client.get("/api/billing-runs", headers=headers_b).get_json() == []


def test_proposal_of_another_tenant_is_not_found(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a, cleanings=3)
    _, proposal_id = _close_september(client, headers_a)

    url = f"/api/proposals/{proposal_id}"
    assert client.get(url, headers=headers_b).status_code == 404
    assert client.post(f"{url}/approve", headers=headers_b).status_code == 404
    assert client.get(f"{url}/pdf", headers=headers_b).status_code == 404

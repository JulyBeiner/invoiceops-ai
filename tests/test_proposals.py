from tests.test_billing_runs import setup_billable_client
from tests.test_clients import auth_header


def close_september(client, headers):
    """Close 2026-09 and return (run, first proposal) as JSON."""
    run = client.post("/api/billing-runs", json={"month": "2026-09"},
                      headers=headers).get_json()
    return run, run["proposals"][0]


def test_get_proposal_shows_lines_with_activities(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)

    response = client.get(f"/api/proposals/{proposal['id']}", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == "701.80"
    assert body["lines"][0]["activities"] == []
    dates = [a["performed_on"] for a in body["lines"][1]["activities"]]
    assert dates[0] == "2026-09-01" and len(dates) == 12


def test_approve_proposal_closes_run_and_cannot_repeat(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)
    run, proposal = close_september(client, headers)
    url = f"/api/proposals/{proposal['id']}/approve"

    response = client.post(url, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["status"] == "approved"

    run_after = client.get(f"/api/billing-runs/{run['id']}",
                           headers=headers).get_json()
    assert run_after["status"] == "closed"

    assert client.post(url, headers=headers).status_code == 409


def test_proposal_of_other_tenant_is_not_found(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a)
    _, proposal = close_september(client, headers_a)

    assert client.get(f"/api/proposals/{proposal['id']}",
                      headers=headers_b).status_code == 404
    assert client.post(f"/api/proposals/{proposal['id']}/approve",
                       headers=headers_b).status_code == 404


def test_download_proposal_pdf(client):
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)
    url = f"/api/proposals/{proposal['id']}/pdf"

    response = client.get(url, headers=headers)
    assert response.mimetype == "application/pdf"
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")
    assert "propuesta" in response.headers["Content-Disposition"]

    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    assert client.get(url, headers=headers_b).status_code == 404

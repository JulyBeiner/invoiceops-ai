from tests.test_clients import auth_header, create_client
from tests.test_contracts import create_service


def setup_client_and_service(client, headers):
    """Create one client and one service; return their ids."""
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]
    return client_id, service_id


def test_create_and_list_activities(client):
    headers = auth_header(client)
    client_id, service_id = setup_client_and_service(client, headers)

    response = client.post("/api/activities", json={
        "client_id": client_id, "service_id": service_id,
        "performed_on": "2026-09-15", "quantity": 2,
    }, headers=headers)
    assert response.status_code == 201
    assert response.get_json()["quantity"] == "2.00"

    client.post("/api/activities", json={
        "client_id": client_id, "service_id": service_id,
        "performed_on": "2026-10-01", "quantity": 1,
    }, headers=headers)

    response = client.get("/api/activities?month=2026-09", headers=headers)
    assert response.status_code == 200
    assert [a["performed_on"] for a in response.get_json()] == ["2026-09-15"]

    response = client.get("/api/activities", headers=headers)
    assert len(response.get_json()) == 2


def test_create_activity_rejects_bad_data(client):
    headers = auth_header(client)
    client_id, service_id = setup_client_and_service(client, headers)
    base = {"client_id": client_id, "service_id": service_id,
            "performed_on": "2026-09-15", "quantity": 1}

    assert client.post("/api/activities", json={**base, "quantity": 0},
                       headers=headers).status_code == 400
    assert client.post("/api/activities", json={**base, "performed_on": "15/09/2026"},
                       headers=headers).status_code == 400
    assert client.post("/api/activities", json={**base, "service_id": 9999},
                       headers=headers).status_code == 400
    assert client.get("/api/activities?month=septiembre",
                      headers=headers).status_code == 400


def test_external_id_is_unique_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client_a, service_a = setup_client_and_service(client, headers_a)
    client_b, service_b = setup_client_and_service(client, headers_b)
    payload_a = {"client_id": client_a, "service_id": service_a,
                 "performed_on": "2026-09-15", "quantity": 1, "external_id": "ROW-1"}
    payload_b = {**payload_a, "client_id": client_b, "service_id": service_b}

    assert client.post("/api/activities", json=payload_a, headers=headers_a).status_code == 201
    assert client.post("/api/activities", json=payload_a, headers=headers_a).status_code == 409
    assert client.post("/api/activities", json=payload_b, headers=headers_b).status_code == 201


def test_activities_are_isolated_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client_a, service_a = setup_client_and_service(client, headers_a)
    payload = {"client_id": client_a, "service_id": service_a,
               "performed_on": "2026-09-15", "quantity": 1}
    client.post("/api/activities", json=payload, headers=headers_a)

    assert client.get("/api/activities", headers=headers_b).get_json() == []
    assert client.post("/api/activities", json=payload, headers=headers_b).status_code == 400

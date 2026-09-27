from tests.test_clients import auth_header


def test_services_require_token(client):
    response = client.get("/api/services")

    assert response.status_code == 401


def test_create_and_list_services(client):
    headers = auth_header(client)

    response = client.post(
        "/api/services",
        json={"name": "Limpieza de oficina", "unit": "visit"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.get_json()["unit"] == "visit"

    response = client.post(
        "/api/services", json={"name": "Hora extra"}, headers=headers)
    assert response.get_json()["unit"] == "unit"

    response = client.get("/api/services", headers=headers)
    names = [s["name"] for s in response.get_json()]
    assert names == ["Hora extra", "Limpieza de oficina"]


def test_create_service_requires_name(client):
    headers = auth_header(client)

    response = client.post("/api/services", json={}, headers=headers)

    assert response.status_code == 400


def test_services_are_isolated_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client.post("/api/services", json={"name": "Solo de A"}, headers=headers_a)

    response = client.get("/api/services", headers=headers_b)

    assert response.get_json() == []

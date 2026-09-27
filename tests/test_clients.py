def auth_header(client, email="july@demo.com", company="Limpiezas Demo"):
    """Register a company and return the Authorization header of its owner."""
    response = client.post("/api/auth/register", json={
        "company_name": company,
        "full_name": "July",
        "email": email,
        "password": "secret123",
    })
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_clients_require_token(client):
    response = client.get("/api/clients")

    assert response.status_code == 401
    assert "message" in response.get_json()


def test_create_and_list_clients(client):
    headers = auth_header(client)

    response = client.post(
        "/api/clients",
        json={"name": "Oficinas Sol", "email": "Sol@Example.com"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Oficinas Sol"
    assert body["email"] == "sol@example.com"
    assert body["is_archived"] is False

    response = client.get("/api/clients", headers=headers)
    assert response.status_code == 200
    assert [c["name"] for c in response.get_json()] == ["Oficinas Sol"]


def test_create_client_requires_name(client):
    headers = auth_header(client)

    response = client.post("/api/clients", json={"name": ""}, headers=headers)

    assert response.status_code == 400


def test_clients_are_isolated_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client.post("/api/clients",
                json={"name": "Cliente de A"}, headers=headers_a)

    response = client.get("/api/clients", headers=headers_b)

    assert response.get_json() == []


def create_client(client, headers, name="Oficinas Sol"):
    """Create a client through the API and return its JSON."""
    return client.post("/api/clients", json={"name": name}, headers=headers).get_json()


def test_get_update_and_archive_client(client):
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]

    response = client.get(f"/api/clients/{client_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Oficinas Sol"

    response = client.put(
        f"/api/clients/{client_id}",
        json={"name": "Oficinas Luna", "tax_id": "B12345678"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "Oficinas Luna"
    assert response.get_json()["tax_id"] == "B12345678"

    response = client.delete(f"/api/clients/{client_id}", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["is_archived"] is True


def test_client_of_another_tenant_is_not_found(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client_id = create_client(client, headers_a)["id"]

    url = f"/api/clients/{client_id}"
    assert client.get(url, headers=headers_b).status_code == 404
    assert client.put(url, json={"name": "Hack"},
                      headers=headers_b).status_code == 404
    assert client.delete(url, headers=headers_b).status_code == 404

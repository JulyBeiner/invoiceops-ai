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

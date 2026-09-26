REGISTER_PAYLOAD = {
    "company_name": "Limpiezas Demo",
    "full_name": "July",
    "email": "july@demo.com",
    "password": "secret123",
}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**REGISTER_PAYLOAD, **overrides})


def test_register_creates_tenant_and_owner(client):
    response = register(client)

    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["email"] == "july@demo.com"
    assert body["user"]["role"] == "owner"
    assert "token" in body


def test_register_rejects_duplicate_email(client):
    register(client)
    response = register(client)

    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = register(client, password="123")

    assert response.status_code == 400


def test_login_returns_token(client):
    register(client)
    response = client.post(
        "/api/auth/login", json={"email": "july@demo.com", "password": "secret123"})

    assert response.status_code == 200
    assert "token" in response.get_json()


def test_login_rejects_wrong_password(client):
    register(client)
    response = client.post(
        "/api/auth/login", json={"email": "july@demo.com", "password": "wrong"})

    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user(client):
    token = register(client).get_json()["token"]
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json()["email"] == "july@demo.com"

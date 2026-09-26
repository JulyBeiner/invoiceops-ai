import re

from api.routes import auth as auth_routes

EMAIL = "july@demo.com"


def register(client):
    return client.post("/api/auth/register", json={
        "company_name": "Limpiezas Demo",
        "full_name": "July",
        "email": EMAIL,
        "password": "secret123",
    })


def test_forgot_and_reset_password_flow(client, monkeypatch):
    sent = {}
    monkeypatch.setattr(auth_routes, "send_email", lambda to,
                        subject, html: sent.update(to=to, html=html) or True)
    register(client)

    response = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    assert sent["to"] == EMAIL
    token = re.search(r"token=([^'\"<]+)", sent["html"]).group(1)

    response = client.post("/api/auth/reset-password",
                           json={"token": token, "password": "newpass123"})
    assert response.status_code == 200

    assert client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "newpass123"}).status_code == 200
    assert client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "secret123"}).status_code == 401


def test_forgot_password_unknown_email_gives_same_message(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_routes, "send_email", lambda to,
                        subject, html: calls.append(to) or True)

    response = client.post("/api/auth/forgot-password",
                           json={"email": "nobody@example.com"})

    assert response.status_code == 200
    assert response.get_json(
    )["message"] == "If that email exists, a reset link has been sent"
    assert calls == []


def test_reset_password_rejects_invalid_token(client):
    response = client.post("/api/auth/reset-password",
                           json={"token": "garbage", "password": "newpass123"})

    assert response.status_code == 400

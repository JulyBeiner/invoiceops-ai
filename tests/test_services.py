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


def test_catalog_lists_standard_services_and_marks_existing(client):
    headers = auth_header(client)
    client.post("/api/services", json={"name": "Limpieza Oficina", "unit": "hora"},
                headers=headers)

    response = client.get("/api/services/catalog", headers=headers)

    assert response.status_code == 200
    catalog = response.get_json()
    assert len(catalog) == 10
    by_name = {item["name"]: item for item in catalog}
    assert by_name["Limpieza de oficina"] == {
        "name": "Limpieza de oficina", "unit": "hora", "exists": True}
    assert by_name["Abrillantado de suelos"]["unit"] == "m²"
    assert by_name["Abrillantado de suelos"]["exists"] is False


def test_catalog_creates_selected_services_and_skips_existing(client):
    headers = auth_header(client)
    client.post("/api/services", json={"name": "Limpieza Oficina", "unit": "hora"},
                headers=headers)

    response = client.post(
        "/api/services/catalog",
        json={"names": ["Limpieza de oficina", "Jardinería", "Desinfección"]},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.get_json()
    assert [(s["name"], s["unit"]) for s in body["created"]] == [
        ("Jardinería", "hora"), ("Desinfección", "servicio")]
    assert body["skipped"] == ["Limpieza de oficina"]
    names = [s["name"]
             for s in client.get("/api/services", headers=headers).get_json()]
    assert names == ["Desinfección", "Jardinería", "Limpieza Oficina"]


def test_catalog_rejects_unknown_names(client):
    headers = auth_header(client)

    response = client.post(
        "/api/services/catalog", json={"names": ["Limpieza espacial"]},
        headers=headers)

    assert response.status_code == 400
    assert "Limpieza espacial" in response.get_json()["message"]

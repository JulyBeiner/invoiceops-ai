from tests.test_clients import auth_header, create_client


def create_service(client, headers, name="Limpieza de oficina"):
    """Create a service through the API and return its JSON."""
    return client.post("/api/services", json={"name": name}, headers=headers).get_json()


def test_set_contract_creates_then_replaces(client):
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]
    url = f"/api/clients/{client_id}/contract"

    response = client.put(url, json={
        "fixed_monthly_fee": "100",
        "prices": [{"service_id": service_id, "unit_price": 40}],
    }, headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["fixed_monthly_fee"] == "100.00"
    assert body["vat_rate"] == "21.00"
    assert len(body["prices"]) == 1
    assert body["prices"][0]["unit_price"] == "40.00"
    contract_id = body["id"]

    response = client.put(url, json={"vat_rate": "10"}, headers=headers)
    body = response.get_json()
    assert body["id"] == contract_id
    assert body["vat_rate"] == "10.00"
    assert body["prices"] == []

    response = client.get(f"/api/clients/{client_id}", headers=headers)
    assert response.get_json()["contract"]["id"] == contract_id


def test_set_contract_rejects_bad_data(client):
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]
    url = f"/api/clients/{client_id}/contract"

    assert client.put(
        url, json={"fixed_monthly_fee": "abc"}, headers=headers).status_code == 400
    assert client.put(
        url, json={"fixed_monthly_fee": "-5"}, headers=headers).status_code == 400
    assert client.put(url, json={"prices": [
                      {"service_id": 9999, "unit_price": 1}]}, headers=headers).status_code == 400
    assert client.put(url, json={"prices": [
        {"service_id": service_id, "unit_price": 1},
        {"service_id": service_id, "unit_price": 2},
    ]}, headers=headers).status_code == 400


def test_contract_is_isolated_per_tenant(client):
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client_id = create_client(client, headers_a)["id"]
    foreign_service_id = create_service(client, headers_b)["id"]
    url = f"/api/clients/{client_id}/contract"

    response = client.put(url, json={
        "prices": [{"service_id": foreign_service_id, "unit_price": 10}],
    }, headers=headers_a)
    assert response.status_code == 400

    response = client.put(url, json={}, headers=headers_b)
    assert response.status_code == 404


def test_set_contract_can_change_the_price_of_the_same_service(client):
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]
    url = f"/api/clients/{client_id}/contract"
    client.put(url, json={"prices": [{"service_id": service_id, "unit_price": 40}]},
               headers=headers)

    response = client.put(url, json={
        "prices": [{"service_id": service_id, "unit_price": "42.50"}],
    }, headers=headers)

    assert response.status_code == 200
    prices = response.get_json()["prices"]
    assert len(prices) == 1
    assert prices[0]["unit_price"] == "42.50"
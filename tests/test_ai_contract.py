from tests.test_ai_capture import fake_ai, upload
from tests.test_clients import auth_header, create_client
from tests.test_contracts import create_service

FAKE_CONTRACT = {
    "fixed_monthly_fee": "250",
    "vat_rate": "21",
    "services": [
        {"name": "limpieza oficina", "unit": "hora", "unit_price": "28,5"},
        {"name": "Jardineria", "unit": "hora", "unit_price": "30"},
        {"name": "Poda de setos", "unit": "servicio", "unit_price": "a convenir"},
    ],
}

CONTRACT_TEXT = ("Cuota fija 250 euros al mes. Limpieza de oficina 28,50 la hora. "
                 "Jardinería 30 la hora. Poda de setos a convenir.")


def test_contract_suggest_parses_text_and_resolves_services(client, monkeypatch):
    calls = fake_ai(monkeypatch, FAKE_CONTRACT)
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]
    service_id = create_service(client, headers)["id"]

    response = client.post(f"/api/clients/{client_id}/contract/suggest",
                           json={"text": CONTRACT_TEXT}, headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["fixed_monthly_fee"] == "250.00"
    assert body["vat_rate"] == "21.00"
    known, catalog, unknown = body["services"]
    # a service the company already has: resolved to its id
    assert known["exists"] is True
    assert known["service_id"] == service_id
    assert known["unit_price"] == "28.50"
    # not in the company, but in the catalog of the niche: offered to create
    assert catalog == {"name": "Jardineria", "unit": "hora", "unit_price": "30.00",
                       "exists": False, "service_id": None,
                       "catalog_match": "Jardinería"}
    # unknown everywhere, unusable price: kept so the person decides
    assert unknown["exists"] is False
    assert unknown["catalog_match"] is None
    assert unknown["unit_price"] is None
    # the prompt lists the company's services and the catalog
    assert "Limpieza de oficina" in calls[0]["prompt"]
    assert "Abrillantado de suelos" in calls[0]["prompt"]
    assert CONTRACT_TEXT in calls[0]["prompt"]
    assert calls[0]["system"]
    # the AI only proposes: no contract was saved
    body = client.get(f"/api/clients/{client_id}", headers=headers).get_json()
    assert body["contract"] is None


def test_contract_suggest_uses_defaults_when_the_ai_omits_them(client, monkeypatch):
    fake_ai(monkeypatch, {"services": []})
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]

    response = client.post(f"/api/clients/{client_id}/contract/suggest",
                           json={"text": "..."}, headers=headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "fixed_monthly_fee": "0.00", "vat_rate": "21.00", "services": []}


def test_contract_suggest_sends_a_photo_to_the_ai(client, monkeypatch):
    calls = fake_ai(monkeypatch, FAKE_CONTRACT)
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]

    response = client.post(f"/api/clients/{client_id}/contract/suggest",
                           data=upload("contrato.jpg",
                                       b"fake-jpg", "image/jpeg"),
                           headers=headers, content_type="multipart/form-data")

    assert response.status_code == 200
    assert calls[0]["images"] == [(b"fake-jpg", "image/jpeg")]
    assert "imagen adjunta" in calls[0]["prompt"]


def test_contract_suggest_requires_text_or_image(client, monkeypatch):
    fake_ai(monkeypatch, FAKE_CONTRACT)
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]
    url = f"/api/clients/{client_id}/contract/suggest"

    empty = client.post(url, json={}, headers=headers)
    assert empty.status_code == 400
    assert empty.get_json()["message"] == "text or an image is required"

    pdf = client.post(url, data=upload("c.pdf", b"%PDF", "application/pdf"),
                      headers=headers, content_type="multipart/form-data")
    assert pdf.status_code == 400
    assert "image" in pdf.get_json()["message"]


def test_contract_suggest_answers_503_when_ai_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    headers = auth_header(client)
    client_id = create_client(client, headers)["id"]

    response = client.post(f"/api/clients/{client_id}/contract/suggest",
                           json={"text": CONTRACT_TEXT}, headers=headers)

    assert response.status_code == 503
    assert response.get_json()["message"] == "AI is not configured"


def test_contract_suggest_of_other_tenant_is_not_found(client, monkeypatch):
    fake_ai(monkeypatch, FAKE_CONTRACT)
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    client_id = create_client(client, headers_a)["id"]

    response = client.post(f"/api/clients/{client_id}/contract/suggest",
                           json={"text": CONTRACT_TEXT}, headers=headers_b)

    assert response.status_code == 404

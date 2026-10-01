from api.services import ai
from tests.test_ai_capture import fake_ai
from tests.test_billing_runs import setup_billable_client
from tests.test_clients import auth_header
from tests.test_proposals import close_september

FAKE_EXPLANATION = {
    "summary": "Propuesta de septiembre: cuota fija y 12 limpiezas.",
    "email_subject": "Propuesta de facturación de septiembre",
    "email_body": "Hola,\n\nAdjuntamos la propuesta de septiembre.\n\nUn saludo",
}


def test_explain_returns_summary_and_email_draft(client, monkeypatch):
    calls = fake_ai(monkeypatch, FAKE_EXPLANATION)
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)

    response = client.get(f"/api/proposals/{proposal['id']}/explain",
                          headers=headers)

    assert response.status_code == 200
    assert response.get_json() == FAKE_EXPLANATION
    # the prompt carries the real figures and names: the AI never calculates
    prompt = calls[0]["prompt"]
    assert "701.80" in prompt
    assert "Oficinas Sol" in prompt
    assert "Limpiezas Demo" in prompt
    assert "septiembre 2026" in prompt
    assert calls[0]["system"]
    # the AI only explains: the proposal is untouched
    body = client.get(f"/api/proposals/{proposal['id']}", headers=headers)
    assert body.get_json()["status"] == "draft"


def test_explain_tolerates_missing_fields(client, monkeypatch):
    fake_ai(monkeypatch, {"summary": "Solo resumen."})
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)

    response = client.get(f"/api/proposals/{proposal['id']}/explain",
                          headers=headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": "Solo resumen.", "email_subject": "", "email_body": ""}


def test_explain_answers_503_when_ai_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)

    response = client.get(f"/api/proposals/{proposal['id']}/explain",
                          headers=headers)

    assert response.status_code == 503
    assert response.get_json()["message"] == "AI is not configured"


def test_explain_reports_a_provider_failure(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")

    def failing(prompt, **kwargs):
        raise ai.AIError("AI provider answered 500: boom")

    monkeypatch.setattr(ai, "complete", failing)
    headers = auth_header(client)
    setup_billable_client(client, headers)
    _, proposal = close_september(client, headers)

    response = client.get(f"/api/proposals/{proposal['id']}/explain",
                          headers=headers)

    assert response.status_code == 502
    assert "AI provider" in response.get_json()["message"]


def test_explain_of_other_tenant_is_not_found(client, monkeypatch):
    fake_ai(monkeypatch, FAKE_EXPLANATION)
    headers_a = auth_header(client, email="a@demo.com", company="Empresa A")
    headers_b = auth_header(client, email="b@demo.com", company="Empresa B")
    setup_billable_client(client, headers_a)
    _, proposal = close_september(client, headers_a)

    response = client.get(f"/api/proposals/{proposal['id']}/explain",
                          headers=headers_b)

    assert response.status_code == 404

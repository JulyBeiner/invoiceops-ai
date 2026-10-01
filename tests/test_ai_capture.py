import io
from datetime import date, timedelta

from api.services import ai
from tests.test_activities import setup_client_and_service
from tests.test_clients import auth_header

FAKE_ANSWER = {"suggestions": [
    {"client": "oficinas sol", "service": "limpieza oficina",
     "performed_on": "15/09/2026", "quantity": "3,5", "external_id": "",
     "note": "Lunes tarde, Ana", "confidence": "high"},
    {"client": "Cliente Fantasma", "service": "Limpieza de oficina",
     "performed_on": "2026-09-16", "quantity": "2", "external_id": "",
     "note": "", "confidence": "low"},
]}


def fake_ai(monkeypatch, answer=FAKE_ANSWER):
    """Pretend the AI is configured and make it answer `answer`.

    Returns the list of calls so a test can inspect the prompt.
    """
    monkeypatch.setenv("AI_API_KEY", "test-key")
    calls = []

    def complete(prompt, **kwargs):
        calls.append({"prompt": prompt, **kwargs})
        return answer

    monkeypatch.setattr(ai, "complete", complete)
    return calls


def upload(name, content, mime_type):
    return {"file": (io.BytesIO(content), name, mime_type)}


def test_suggest_answers_503_when_ai_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    headers = auth_header(client)

    response = client.post("/api/activities/suggest",
                           json={"text": "Lunes 3 horas en Oficinas Sol"},
                           headers=headers)

    assert response.status_code == 503
    assert response.get_json()["message"] == "AI is not configured"


def test_suggest_requires_text(client, monkeypatch):
    fake_ai(monkeypatch)
    headers = auth_header(client)

    response = client.post("/api/activities/suggest", json={}, headers=headers)

    assert response.status_code == 400
    assert response.get_json()["message"] == "text is required"


def test_suggest_matches_names_and_parses_spanish_formats(client, monkeypatch):
    calls = fake_ai(monkeypatch)
    headers = auth_header(client)
    client_id, service_id = setup_client_and_service(client, headers)

    response = client.post("/api/activities/suggest",
                           json={"text": "Lunes 3,5h en oficinas sol"},
                           headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    first, second = body["suggestions"]
    assert first["resolved"] == {
        "client_id": client_id, "service_id": service_id}
    assert first["performed_on"] == "2026-09-15"
    assert first["quantity"] == "3.50"
    assert first["confidence"] == "high"
    assert first["note"] == "Lunes tarde, Ana"
    # unknown client: the name is kept so the person can choose, nothing guessed
    assert second["client"] == "Cliente Fantasma"
    assert second["resolved"] == {"client_id": None, "service_id": service_id}
    # the AI only proposes: nothing was written
    assert client.get("/api/activities", headers=headers).get_json() == []
    # the prompt tells the model which clients and services exist
    assert "Oficinas Sol" in calls[0]["prompt"]
    assert "Limpieza de oficina" in calls[0]["prompt"]
    assert calls[0]["system"]
    yesterday = date.today() - timedelta(days=1)
    assert yesterday.strftime("%d/%m/%Y") in calls[0]["prompt"]


def test_suggest_tolerates_unusable_ai_values(client, monkeypatch):
    fake_ai(monkeypatch, {"suggestions": [
        {"client": "x", "service": "y", "performed_on": "ayer",
         "quantity": "muchas"}]})
    headers = auth_header(client)

    response = client.post("/api/activities/suggest", json={"text": "..."},
                           headers=headers)

    assert response.status_code == 200
    suggestion = response.get_json()["suggestions"][0]
    assert suggestion["performed_on"] is None
    assert suggestion["quantity"] is None
    assert suggestion["confidence"] == "low"
    assert suggestion["resolved"] == {"client_id": None, "service_id": None}


def test_suggest_reports_a_provider_failure(client, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")

    def failing(prompt, **kwargs):
        raise ai.AIError("AI provider answered 500: boom")

    monkeypatch.setattr(ai, "complete", failing)
    headers = auth_header(client)

    response = client.post("/api/activities/suggest", json={"text": "..."},
                           headers=headers)

    assert response.status_code == 502
    assert "AI provider" in response.get_json()["message"]


def test_suggest_sends_a_photo_to_the_ai(client, monkeypatch):
    calls = fake_ai(monkeypatch)
    headers = auth_header(client)
    setup_client_and_service(client, headers)

    response = client.post("/api/activities/suggest",
                           data=upload("parte.png", b"fake-png", "image/png"),
                           headers=headers, content_type="multipart/form-data")

    assert response.status_code == 200
    assert calls[0]["images"] == [(b"fake-png", "image/png")]
    assert "imagen adjunta" in calls[0]["prompt"]
    assert len(response.get_json()["suggestions"]) == 2


def test_suggest_transcribes_a_voice_note_first(client, monkeypatch):
    calls = fake_ai(monkeypatch)
    heard = []

    def transcribe(data, filename, mime_type):
        heard.append((data, filename, mime_type))
        return "Lunes 3,5 horas en Oficinas Sol"

    monkeypatch.setattr(ai, "transcribe", transcribe)
    headers = auth_header(client)
    setup_client_and_service(client, headers)

    response = client.post("/api/activities/suggest",
                           data=upload("nota.ogg", b"fake-ogg", "audio/ogg"),
                           headers=headers, content_type="multipart/form-data")

    assert response.status_code == 200
    assert heard == [(b"fake-ogg", "nota.ogg", "audio/ogg")]
    assert response.get_json(
    )["transcript"] == "Lunes 3,5 horas en Oficinas Sol"
    assert "Lunes 3,5 horas en Oficinas Sol" in calls[0]["prompt"]


def test_suggest_rejects_other_file_types(client, monkeypatch):
    fake_ai(monkeypatch)
    headers = auth_header(client)

    response = client.post("/api/activities/suggest",
                           data=upload("doc.pdf", b"%PDF", "application/pdf"),
                           headers=headers, content_type="multipart/form-data")

    assert response.status_code == 400
    assert "image" in response.get_json()["message"]

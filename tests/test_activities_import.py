import io

from tests.test_activities import setup_client_and_service
from tests.test_clients import auth_header

HEADER = "external_id,client,service,performed_on,quantity\n"


def upload(client, headers, content, commit=False):
    """Upload a CSV text to the import endpoint."""
    url = "/api/activities/import" + ("?commit=true" if commit else "")
    return client.post(
        url,
        data={"file": (io.BytesIO(content.encode("utf-8")), "activities.csv")},
        content_type="multipart/form-data",
        headers=headers,
    )


def test_import_preview_does_not_save(client):
    headers = auth_header(client)
    setup_client_and_service(client, headers)
    csv_text = HEADER + "A1,Oficinas Sol,Limpieza de oficina,2026-09-10,2\n"

    response = upload(client, headers, csv_text)

    assert response.status_code == 200
    body = response.get_json()
    assert body["committed"] is False
    assert body["summary"] == {"ok": 1, "errors": 0, "duplicates": 0}
    assert client.get("/api/activities", headers=headers).get_json() == []


def test_import_commit_saves_valid_rows_and_reports_errors(client):
    headers = auth_header(client)
    setup_client_and_service(client, headers)
    csv_text = HEADER + (
        "A1,Oficinas Sol,Limpieza de oficina,2026-09-10,2\n"
        "A2,Cliente Fantasma,Limpieza de oficina,2026-09-11,1\n"
        "A3,oficinas sol,Limpieza de oficina,2026-09-12,0\n"
        "A1,Oficinas Sol,Limpieza de oficina,2026-09-13,1\n"
    )

    response = upload(client, headers, csv_text, commit=True)

    body = response.get_json()
    assert body["committed"] is True
    assert body["summary"] == {"ok": 1, "errors": 2, "duplicates": 1}
    assert [row["status"] for row in body["rows"]] == [
        "ok", "error", "error", "duplicate"]
    assert body["rows"][1]["message"] == "client not found"
    assert len(client.get("/api/activities", headers=headers).get_json()) == 1


def test_import_skips_rows_already_imported(client):
    headers = auth_header(client)
    setup_client_and_service(client, headers)
    csv_text = HEADER + "A1,Oficinas Sol,Limpieza de oficina,2026-09-10,2\n"

    upload(client, headers, csv_text, commit=True)
    response = upload(client, headers, csv_text, commit=True)

    assert response.get_json()["summary"] == {
        "ok": 0, "errors": 0, "duplicates": 1}
    assert len(client.get("/api/activities", headers=headers).get_json()) == 1


def test_import_rejects_malformed_file(client):
    headers = auth_header(client)

    response = upload(client, headers, "name,date\nfoo,bar\n", commit=True)
    assert response.status_code == 400
    assert "missing columns" in response.get_json()["message"]

    response = client.post(
        "/api/activities/import?commit=true", headers=headers)
    assert response.status_code == 400


def test_import_matches_names_loosely_and_reports_the_match(client):
    headers = auth_header(client)
    setup_client_and_service(client, headers)
    csv_text = HEADER + (
        "A1,oficinas sol,LIMPIEZA OFICINA,2026-09-10,2\n"
        "A2,Oficinas Sól S.L.,Limpieza de oficinas,2026-09-11,1\n"
        "A3,Talleres Vega,Limpieza de oficina,2026-09-12,1\n"
    )

    body = upload(client, headers, csv_text).get_json()

    assert body["summary"] == {"ok": 2, "errors": 1, "duplicates": 0}
    first, second, third = body["rows"]
    assert first["resolved"] == {"client": "Oficinas Sol",
                                 "service": "Limpieza de oficina"}
    assert second["resolved"]["client"] == "Oficinas Sol"
    assert third["status"] == "error" and "client" in third["message"]

from api.extensions import db
from api.models import Activity, Client, Service, Tenant

DEMO_LOGIN = {"email": "july@limpiezasaurora.es", "password": "Aurora2026!"}


def run_seed(app, *args):
    result = app.test_cli_runner().invoke(args=["seed", *args])
    assert result.exit_code == 0, result.output
    return result.output


def demo_tenant():
    return db.session.scalar(
        db.select(Tenant).filter_by(name="Limpiezas Aurora S.L."))


def count(model, tenant_id):
    return len(db.session.scalars(
        db.select(model).filter_by(tenant_id=tenant_id)).all())


def test_seed_creates_the_demo_company(app, client):
    output = run_seed(app)

    assert "Demo company loaded: Limpiezas Aurora S.L." in output
    tenant = demo_tenant()
    assert count(Service, tenant.id) == 3
    assert count(Client, tenant.id) == 4
    assert count(Activity, tenant.id) == 50
    response = client.post("/api/auth/login", json=DEMO_LOGIN)
    assert response.status_code == 200
    assert response.get_json(
    )["user"]["tenant_name"] == "Limpiezas Aurora S.L."


def test_seed_does_nothing_when_the_demo_company_exists(app):
    run_seed(app)
    output = run_seed(app)

    assert "already exists" in output
    tenants = db.session.scalars(
        db.select(Tenant).filter_by(name="Limpiezas Aurora S.L.")).all()
    assert len(tenants) == 1
    assert count(Activity, tenants[0].id) == 50


def test_seed_reset_reloads_the_demo_company_even_after_a_month_close(app, client):
    run_seed(app)
    token = client.post("/api/auth/login", json=DEMO_LOGIN).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/billing-runs", json={"month": "2026-09"},
                       headers=headers).status_code == 201
    other = client.post("/api/auth/register", json={
        "company_name": "Otra Empresa", "full_name": "Ana",
        "email": "ana@otra.es", "password": "Secreta123"})
    assert other.status_code == 201

    output = run_seed(app, "--reset")

    assert "Deleting demo company" in output
    assert "Demo company loaded" in output
    tenant = demo_tenant()
    assert count(Client, tenant.id) == 4
    assert count(Activity, tenant.id) == 50
    assert client.post("/api/auth/login", json={
        "email": "ana@otra.es", "password": "Secreta123"}).status_code == 200


def test_seed_september_closes_with_the_expected_totals(app, client):
    run_seed(app)
    token = client.post("/api/auth/login", json=DEMO_LOGIN).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/billing-runs", json={"month": "2026-09"},
                           headers=headers)

    assert response.status_code == 201
    body = response.get_json()
    totals = {p["client_name"]: p["total"] for p in body["proposals"]}
    assert totals == {
        "Oficinas Sol": "1952.94",
        "Clínica Dental Ruiz": "862.13",
        "Gimnasio Norte": "866.36",
        "Farmacia Central": "217.80",
    }
    assert [c["client_name"] for c in body["clients_without_activity"]] == [
        "Farmacia Central"]

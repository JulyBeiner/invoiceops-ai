"""
Flask CLI commands.

`flask seed` loads the demo company used in the GeekTalk and on Render:
tenant, owner, services, clients with contracts, and September + October
2026 activities. It is idempotent: a second run does nothing unless
`--reset` is given, which deletes the demo company first and loads it again.
Run it with `pipenv run seed` or `pipenv run seed --reset`.
"""
from datetime import date, timedelta
from decimal import Decimal

import click

from api.extensions import db
from api.models import (Activity, BillingRun, Client, Contract,
                        ContractPrice, Service, Tenant, User)

DEMO_COMPANY = {"name": "Limpiezas Aurora S.L.", "tax_id": "B98765432"}

DEMO_OWNER = {
    "full_name": "July Beiner",
    "email": "july@limpiezasaurora.es",
    "password": "Aurora2026!",
}

# Service name -> unit. The end user reads these, so they are in Spanish.
DEMO_SERVICES = {
    "Limpieza de oficina": "hora",
    "Limpieza de cristales": "unidad",
    "Mantenimiento": "hora",
}

# One entry per client: fixed monthly fee and one price per contracted service.
DEMO_CLIENTS = [
    {
        "name": "Oficinas Sol",
        "tax_id": "B12345678",
        "email": "admin@oficinassol.es",
        "fee": "250.00",
        "prices": {"Limpieza de oficina": "28.00",
                   "Limpieza de cristales": "45.00"},
    },
    {
        "name": "Clínica Dental Ruiz",
        "tax_id": "B23456789",
        "email": "gerencia@clinicaruiz.es",
        "fee": "120.00",
        "prices": {"Limpieza de oficina": "30.00",
                   "Mantenimiento": "35.00"},
    },
    {
        "name": "Gimnasio Norte",
        "tax_id": "B34567890",
        "email": "info@gimnasionorte.es",
        "fee": "0.00",
        "prices": {"Limpieza de oficina": "26.00",
                   "Limpieza de cristales": "40.00"},
    },
    {
        # Contract but no activities: the "revisar antes de cerrar" case.
        "name": "Farmacia Central",
        "tax_id": "B45678901",
        "email": "farmacia@central.es",
        "fee": "180.00",
        "prices": {"Limpieza de oficina": "28.00"},
    },
]

# Recurring visits: (client, service, weekdays with Monday = 0, quantity).
DEMO_SCHEDULE = [
    ("Oficinas Sol", "Limpieza de oficina", (0, 2, 4), "3.50"),
    ("Clínica Dental Ruiz", "Limpieza de oficina", (1, 3), "2.00"),
    ("Gimnasio Norte", "Limpieza de oficina", (0, 2, 4), "2.00"),
]

# One-off jobs: (client, service, date, quantity).
DEMO_ONE_OFFS = [
    ("Oficinas Sol", "Limpieza de cristales", date(2026, 9, 17), "2.00"),
    ("Clínica Dental Ruiz", "Mantenimiento", date(2026, 9, 22), "1.50"),
    ("Gimnasio Norte", "Limpieza de cristales", date(2026, 9, 24), "1.00"),
    ("Clínica Dental Ruiz", "Mantenimiento", date(2026, 10, 6), "1.00"),
]

# September complete; October only up to the 9th so it looks in progress.
DEMO_PERIODS = [
    (date(2026, 9, 1), date(2026, 9, 30)),
    (date(2026, 10, 1), date(2026, 10, 9)),
]


def _days(first, last):
    """Yield every date from first to last, both included."""
    day = first
    while day <= last:
        yield day
        day += timedelta(days=1)


def _find_demo_owner():
    return db.session.scalar(
        db.select(User).filter_by(email=DEMO_OWNER["email"]))


def _delete_tenant(tenant):
    """Delete a tenant and everything it owns, children before parents."""
    # 1. Activities and billing runs (runs cascade to proposals and lines).
    for activity in db.session.scalars(
            db.select(Activity).filter_by(tenant_id=tenant.id)):
        db.session.delete(activity)
    for run in db.session.scalars(
            db.select(BillingRun).filter_by(tenant_id=tenant.id)):
        db.session.delete(run)
    db.session.flush()
    # 2. Contracts (cascade to prices), clients, services and users.
    for client in tenant.clients:
        for contract in client.contracts:
            db.session.delete(contract)
        db.session.delete(client)
    for service in tenant.services:
        db.session.delete(service)
    for user in tenant.users:
        db.session.delete(user)
    db.session.flush()
    # 3. The tenant itself.
    db.session.delete(tenant)
    db.session.commit()


def _create_demo():
    """Create the demo company. Returns (tenant, list of activities)."""
    tenant = Tenant(**DEMO_COMPANY)
    owner = User(tenant=tenant, email=DEMO_OWNER["email"],
                 full_name=DEMO_OWNER["full_name"], role="owner")
    owner.set_password(DEMO_OWNER["password"])
    db.session.add(owner)

    services = {name: Service(tenant=tenant, name=name, unit=unit)
                for name, unit in DEMO_SERVICES.items()}
    db.session.add_all(services.values())

    clients = {}
    for data in DEMO_CLIENTS:
        client = Client(tenant=tenant, name=data["name"],
                        tax_id=data["tax_id"], email=data["email"])
        contract = Contract(client=client,
                            fixed_monthly_fee=Decimal(data["fee"]),
                            vat_rate=Decimal("21.00"))
        contract.prices = [
            ContractPrice(service=services[name], unit_price=Decimal(price))
            for name, price in data["prices"].items()
        ]
        db.session.add(contract)
        clients[data["name"]] = client
    db.session.flush()  # gives the tenant its id, needed by Activity

    activities = []
    for first, last in DEMO_PERIODS:
        for client_name, service_name, weekdays, quantity in DEMO_SCHEDULE:
            for day in _days(first, last):
                if day.weekday() in weekdays:
                    activities.append(Activity(
                        tenant_id=tenant.id, client=clients[client_name],
                        service=services[service_name], performed_on=day,
                        quantity=Decimal(quantity)))
    for client_name, service_name, day, quantity in DEMO_ONE_OFFS:
        activities.append(Activity(
            tenant_id=tenant.id, client=clients[client_name],
            service=services[service_name], performed_on=day,
            quantity=Decimal(quantity)))
    db.session.add_all(activities)
    db.session.commit()
    return tenant, activities


def setup_commands(app):

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True,
                  help="Delete the demo company first and load it again.")
    def seed(reset):
        """Load the demo company (Limpiezas Aurora S.L.) with its data."""
        owner = _find_demo_owner()
        if owner is not None and not reset:
            click.echo(f"Demo company already exists: {owner.tenant.name} "
                       "- nothing to do (use --reset to load it again).")
            return
        if owner is not None:
            click.echo(f"Deleting demo company: {owner.tenant.name}")
            _delete_tenant(owner.tenant)

        tenant, activities = _create_demo()
        per_month = {}
        for activity in activities:
            key = activity.performed_on.strftime("%Y-%m")
            per_month[key] = per_month.get(key, 0) + 1
        months = ", ".join(f"{k}: {v}" for k, v in sorted(per_month.items()))
        click.echo(f"Demo company loaded: {tenant.name}")
        click.echo(
            f"  login: {DEMO_OWNER['email']} / {DEMO_OWNER['password']}")
        click.echo(f"  services: {len(DEMO_SERVICES)}, clients: "
                   f"{len(DEMO_CLIENTS)}, activities: {len(activities)} "
                   f"({months})")

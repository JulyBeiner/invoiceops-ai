"""Billing engine: pure Python, no Flask, no database.

Receives a contract and the activities of one month as plain dicts and
returns the proposal lines and totals. Prices and totals are only ever
computed here.
"""
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
FIXED_FEE_DESCRIPTION = "Cuota fija mensual"


def money(value):
    """Round a Decimal to 2 decimals, half up (0.005 -> 0.01)."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def build_proposal(contract, activities):
    """Group activities by service, price them and compute totals.

    contract: {"fixed_monthly_fee", "vat_rate", "prices": {service_id: unit_price}}
    activities: [{"id", "service_id", "service_name", "quantity"}, ...]
    """
    lines = []
    unpriced = []

    fee = money(contract["fixed_monthly_fee"])
    if fee > 0:
        lines.append({
            "service_id": None,
            "description": FIXED_FEE_DESCRIPTION,
            "quantity": Decimal("1.00"),
            "unit_price": fee,
            "amount": fee,
            "activity_ids": [],
        })

    grouped = {}
    for act in activities:
        price = contract["prices"].get(act["service_id"])
        if price is None:
            unpriced.append(act["id"])
            continue
        group = grouped.setdefault(act["service_id"], {
            "service_id": act["service_id"],
            "description": act["service_name"],
            "quantity": Decimal("0.00"),
            "unit_price": money(price),
            "activity_ids": [],
        })
        group["quantity"] += act["quantity"]
        group["activity_ids"].append(act["id"])

    for group in grouped.values():
        group["quantity"] = money(group["quantity"])
        group["amount"] = money(group["quantity"] * group["unit_price"])
        lines.append(group)

    subtotal = money(sum((line["amount"] for line in lines), Decimal("0")))
    vat_amount = money(subtotal * money(contract["vat_rate"]) / 100)

    return {
        "lines": lines,
        "subtotal": subtotal,
        "vat_amount": vat_amount,
        "total": money(subtotal + vat_amount),
        "unpriced_activity_ids": unpriced,
    }

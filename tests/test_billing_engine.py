from decimal import Decimal

from api.services.billing import build_proposal


def contract(fee="0.00", vat="21.00", prices=None):
    return {
        "fixed_monthly_fee": Decimal(fee),
        "vat_rate": Decimal(vat),
        "prices": prices or {},
    }


def activity(id, service_id, quantity, service_name="Limpieza"):
    return {
        "id": id,
        "service_id": service_id,
        "service_name": service_name,
        "quantity": Decimal(quantity),
    }


def test_twelve_cleanings_at_forty_with_vat():
    acts = [activity(i, 1, "1.00") for i in range(1, 13)]
    result = build_proposal(contract(prices={1: Decimal("40.00")}), acts)

    assert len(result["lines"]) == 1
    line = result["lines"][0]
    assert line["quantity"] == Decimal("12.00")
    assert line["unit_price"] == Decimal("40.00")
    assert line["amount"] == Decimal("480.00")
    assert line["activity_ids"] == list(range(1, 13))
    assert result["subtotal"] == Decimal("480.00")
    assert result["vat_amount"] == Decimal("100.80")
    assert result["total"] == Decimal("580.80")
    assert result["unpriced_activity_ids"] == []


def test_fixed_fee_alone():
    result = build_proposal(contract(fee="300.00"), [])

    assert len(result["lines"]) == 1
    line = result["lines"][0]
    assert line["service_id"] is None
    assert line["description"] == "Cuota fija mensual"
    assert line["amount"] == Decimal("300.00")
    assert result["total"] == Decimal("363.00")


def test_activity_without_price_is_flagged_not_billed():
    acts = [activity(1, 1, "2.00"), activity(2, 9, "1.00", "Cristales")]
    result = build_proposal(contract(prices={1: Decimal("10.00")}), acts)

    assert len(result["lines"]) == 1
    assert result["subtotal"] == Decimal("20.00")
    assert result["unpriced_activity_ids"] == [2]


def test_nothing_to_bill():
    result = build_proposal(contract(), [])

    assert result["lines"] == []
    assert result["total"] == Decimal("0.00")

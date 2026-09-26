from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import db
from api.models.base import TimestampMixin


class Contract(TimestampMixin, db.Model):
    __tablename__ = "contract"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True)
    fixed_monthly_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("21.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean(), default=True, nullable=False)

    client = relationship("Client", backref="contracts")
    prices = relationship(
        "ContractPrice", back_populates="contract",
        cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "fixed_monthly_fee": str(self.fixed_monthly_fee),
            "vat_rate": str(self.vat_rate),
            "is_active": self.is_active,
            "prices": [price.serialize() for price in self.prices],
        }


class ContractPrice(db.Model):
    __tablename__ = "contract_price"
    __table_args__ = (
        UniqueConstraint("contract_id", "service_id",
                         name="uq_contract_price_service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contract.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("service.id"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False)

    contract = relationship("Contract", back_populates="prices")
    service = relationship("Service")

    def serialize(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "unit_price": str(self.unit_price),
        }

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import db
from api.models.base import TimestampMixin


class Activity(TimestampMixin, db.Model):
    __tablename__ = "activity"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id",
                         name="uq_activity_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("service.id"), nullable=False)
    performed_on: Mapped[date] = mapped_column(
        Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(80))

    client = relationship("Client", backref="activities")
    service = relationship("Service")

    def serialize(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "service_id": self.service_id,
            "performed_on": self.performed_on.isoformat(),
            "quantity": str(self.quantity),
            "external_id": self.external_id,
        }

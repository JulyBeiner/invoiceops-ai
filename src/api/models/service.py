from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import db
from api.models.base import TimestampMixin


class Service(TimestampMixin, db.Model):
    __tablename__ = "service"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(20), default="unit", nullable=False)

    tenant = relationship("Tenant", backref="services")

    def serialize(self):
        return {"id": self.id, "name": self.name, "unit": self.unit}

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import db
from api.models.base import TimestampMixin


class Client(TimestampMixin, db.Model):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(120))
    is_archived: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False)

    tenant = relationship("Tenant", backref="clients")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "tax_id": self.tax_id,
            "email": self.email,
            "is_archived": self.is_archived,
        }

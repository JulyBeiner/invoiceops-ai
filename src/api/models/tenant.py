from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.extensions import db
from api.models.base import TimestampMixin


class Tenant(TimestampMixin, db.Model):
    __tablename__ = "tenant"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(20))

    def serialize(self):
        return {"id": self.id, "name": self.name, "tax_id": self.tax_id}

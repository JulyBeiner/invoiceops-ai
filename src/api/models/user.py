from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import bcrypt, db
from api.models.base import TimestampMixin

ROLES = ("owner", "admin", "operator")


class User(TimestampMixin, db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="owner", nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean(), default=True, nullable=False)

    tenant = relationship("Tenant", backref="users")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(
            password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def serialize(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }

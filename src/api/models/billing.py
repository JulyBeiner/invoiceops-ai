from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.extensions import db
from api.models.base import TimestampMixin


class BillingRun(TimestampMixin, db.Model):
    """One month-end close per tenant and month."""
    __tablename__ = "billing_run"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", "month",
                         name="uq_billing_run_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenant.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False)

    proposals = relationship(
        "Proposal", back_populates="billing_run",
        cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "status": self.status,
            "proposals": [p.serialize() for p in self.proposals],
        }


class Proposal(TimestampMixin, db.Model):
    """The invoice proposal of one client inside a billing run."""
    __tablename__ = "proposal"
    __table_args__ = (
        UniqueConstraint("billing_run_id", "client_id",
                         name="uq_proposal_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    billing_run_id: Mapped[int] = mapped_column(
        ForeignKey("billing_run.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    billing_run = relationship("BillingRun", back_populates="proposals")
    client = relationship("Client")
    lines = relationship(
        "ProposalLine", back_populates="proposal",
        cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "billing_run_id": self.billing_run_id,
            "client_id": self.client_id,
            "client_name": self.client.name,
            "status": self.status,
            "subtotal": str(self.subtotal),
            "vat_amount": str(self.vat_amount),
            "total": str(self.total),
            "lines": [line.serialize() for line in self.lines],
        }


class ProposalLine(db.Model):
    """One line of a proposal: a service grouped, or the fixed fee."""
    __tablename__ = "proposal_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("proposal.id"), nullable=False, index=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("service.id"))
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    proposal = relationship("Proposal", back_populates="lines")
    activities = relationship("Activity", backref="proposal_line")

    def serialize(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "amount": str(self.amount),
            "activity_ids": [a.id for a in self.activities],
        }

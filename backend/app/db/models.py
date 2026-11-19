"""Initial schema: exact decimal TEXT, no analysis-to-ledger relationships."""
from decimal import Decimal
from sqlalchemy import String, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

class DecimalText(TypeDecorator):
    impl = String
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("Finite Decimal required")
        return str(value)
    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)

class Base(DeclarativeBase):
    pass

class Vendor(Base):
    __tablename__ = "vendor"
    id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

class PurchaseOrder(Base):
    __tablename__ = "purchase_order"
    id: Mapped[str] = mapped_column(primary_key=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendor.id"))
    authorized_net: Mapped[Decimal] = mapped_column(DecimalText)
    payload: Mapped[dict] = mapped_column(JSON)

class POLine(Base):
    __tablename__ = "po_line"
    __table_args__ = (UniqueConstraint("po_id", "item_code"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"))
    item_code: Mapped[str]
    ordered_qty: Mapped[Decimal] = mapped_column(DecimalText)
    unit_price_net: Mapped[Decimal] = mapped_column(DecimalText)
    authorized_net: Mapped[Decimal] = mapped_column(DecimalText)

class PriorBilledInvoice(Base):
    __tablename__ = "prior_billed_invoice"
    id: Mapped[str] = mapped_column(primary_key=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendor.id"))
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"))
    net: Mapped[Decimal] = mapped_column(DecimalText)
    payload: Mapped[dict] = mapped_column(JSON)

class PolicySnapshot(Base):
    __tablename__ = "policy_snapshot"
    version: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

class InvoiceRun(Base):
    __tablename__ = "invoice_run"
    id: Mapped[str] = mapped_column(primary_key=True)
    # Validated RunSnapshotV1 JSON is the versioned analysis boundary.
    # No hooks, relationships, or balance-consumption writes.
    payload: Mapped[dict] = mapped_column(JSON)

class RunStage(Base):
    __tablename__ = "run_stage"
    id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("invoice_run.id"))
    payload: Mapped[dict] = mapped_column(JSON)


class ReviewAction(Base):
    """One append-only confirmation plus its full typed assessment, atomically committed."""
    __tablename__ = "review_action"
    id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("invoice_run.id"), unique=True)
    client_action_id: Mapped[str] = mapped_column(String(36))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)

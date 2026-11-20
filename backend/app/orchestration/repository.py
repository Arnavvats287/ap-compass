"""Short run transactions; stage rows are the only stage source of truth."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.contracts import (RunSnapshotV1, RunStageV1, PolicyV1, VendorV1,
                           PurchaseOrderV1, PriorBilledInvoiceV1, ExtractedInvoiceV1)
from app.db.models import (InvoiceRun, RunStage, PolicySnapshot, Vendor,
                           PurchaseOrder, PriorBilledInvoice, ReviewAction)
from app.domain.controls import verified_invoice_number
from app.domain.common import normalized
from app.domain.matching import resolve_vendor

def load_authority(session):
    return tuple(tuple(contract.model_validate(row.payload) for row in session.scalars(select(model).order_by(model.id)))
                 for model, contract in ((Vendor,VendorV1),(PurchaseOrder,PurchaseOrderV1),
                                         (PriorBilledInvoice,PriorBilledInvoiceV1)))


STAGES = ("received", "extracting_invoice", "matching_records", "evaluating_controls", "finalizing")


def now():
    return datetime.now(timezone.utc)


class RunRepository:
    def __init__(self, engine):
        self.engine = engine

    def create(self, document_id, *, policy_snapshot=None, document_sha256=None):
        timestamp = now()
        snapshot = RunSnapshotV1(id=uuid4().hex, execution_state="QUEUED", document_id=document_id,
                                 policy_snapshot=policy_snapshot, created_at=timestamp, updated_at=timestamp)
        with Session(self.engine) as session, session.begin():
            if document_sha256 is not None:
                # Serialize the lookup and insert so simultaneous repeats share one run.
                session.execute(text("BEGIN IMMEDIATE"))
                existing = session.scalar(select(InvoiceRun.payload).where(
                    InvoiceRun.document_sha256 == document_sha256,
                    InvoiceRun.payload["policy_snapshot"]["version"].as_string() == policy_snapshot.version,
                    InvoiceRun.payload["execution_state"].as_string().in_(("QUEUED", "RUNNING", "COMPLETED")),
                ).order_by(InvoiceRun.payload["created_at"].as_string(), InvoiceRun.id).limit(1))
                if existing is not None:
                    return RunSnapshotV1.model_validate({**existing, "stages": ()})
            session.add(InvoiceRun(id=snapshot.id, payload=snapshot.model_dump(mode="json"),
                                   document_sha256=document_sha256))
            session.flush()
            for name in STAGES:
                stage = RunStageV1(name=name, state="PASSED" if name == "received" else "QUEUED",
                                   started_at=timestamp if name == "received" else None,
                                   finished_at=timestamp if name == "received" else None)
                session.add(RunStage(id=f"{snapshot.id}:{name}", run_id=snapshot.id,
                                     payload=stage.model_dump(mode="json")))
        return snapshot

    def prior_verified_submission(self, current_id, vendor, invoice, vendors):
        number = verified_invoice_number(invoice)
        if vendor is None or not vendor.approved or not number:
            return None
        # Include pre-migration submissions and the full history, beyond the UI list limit.
        statement = select(InvoiceRun.id, InvoiceRun.payload["extracted_invoice"]).where(
            InvoiceRun.id != current_id,
            InvoiceRun.payload["execution_state"].as_string() == "COMPLETED",
        ).order_by(InvoiceRun.payload["created_at"].as_string(), InvoiceRun.id)
        with Session(self.engine) as session:
            for run_id, payload in session.execute(statement.execution_options(yield_per=100)):
                if payload is None or normalized(payload.get("invoice_number")) != number:
                    continue
                earlier = ExtractedInvoiceV1.model_validate(payload)
                if verified_invoice_number(earlier) != number:
                    continue
                earlier_vendor = resolve_vendor(earlier.vendor_name_raw, vendors)
                if earlier_vendor is not None and earlier_vendor.id == vendor.id:
                    return run_id
        return None

    def load(self, run_id):
        with Session(self.engine) as session:
            # One statement gives run + stage rows a single SQLite read snapshot,
            # including under Python sqlite3's legacy transaction behavior.
            rows = session.execute(select(InvoiceRun, RunStage).outerjoin(
                RunStage, RunStage.run_id == InvoiceRun.id).where(InvoiceRun.id == run_id)).all()
            if not rows:
                return None
            row = rows[0][0]
            stages = {stage.payload["name"]: stage.payload for _, stage in rows if stage is not None}
            # Ignore any legacy embedded stages. They cannot override authoritative rows.
            return RunSnapshotV1.model_validate({**row.payload, "stages": [stages[name] for name in STAGES if name in stages]})

    def update(self, run_id, *, stages=None, **changes):
        with Session(self.engine) as session, session.begin():
            row = session.get(InvoiceRun, run_id)
            snapshot = RunSnapshotV1.model_validate({**row.payload, **changes, "stages": (), "updated_at": now()})
            row.payload = snapshot.model_dump(mode="json")
            for name, state in (stages or {}).items():
                stage_row = session.get(RunStage, f"{run_id}:{name}")
                values = dict(stage_row.payload, state=state)
                timestamp = now()
                if state == "RUNNING":
                    values["started_at"] = timestamp
                elif state in ("PASSED", "FAILED", "SKIPPED", "WARNING"):
                    values["finished_at"] = timestamp
                stage_row.payload = RunStageV1.model_validate(values).model_dump(mode="json")

    def terminate(self, run_id, code, *, interrupted=False):
        snapshot = self.load(run_id)
        stages = {stage.name: "FAILED" if stage.state == "RUNNING" else "SKIPPED"
                  for stage in snapshot.stages if stage.state in ("RUNNING", "QUEUED")}
        self.update(run_id, stages=stages, execution_state="INTERRUPTED" if interrupted else "PROCESSING_FAILED",
                    execution_error_code=code, decision=None)

    def reconcile(self):
        for snapshot in self.all():
            if snapshot.execution_state in ("QUEUED", "RUNNING"):
                self.terminate(snapshot.id, "SERVER_RESTART", interrupted=True)

    def all(self, limit=None):
        # One query, no stage/authority queries per row; timestamps are UTC ISO strings.
        statement = select(InvoiceRun).order_by(InvoiceRun.payload["created_at"].as_string().desc(), InvoiceRun.id)
        if limit is not None:
            statement = statement.limit(limit)
        with Session(self.engine) as session:
            return [RunSnapshotV1.model_validate({**row.payload, "stages": ()}) for row in session.scalars(statement)]

    def all_with_reviews(self, limit):
        statement=select(InvoiceRun,ReviewAction).outerjoin(ReviewAction,ReviewAction.run_id==InvoiceRun.id).order_by(
            InvoiceRun.payload["created_at"].as_string().desc(),InvoiceRun.id).limit(limit)
        with Session(self.engine) as session:
            return [(RunSnapshotV1.model_validate({**run.payload,"stages":()}),review.payload if review else None)
                    for run,review in session.execute(statement)]

    def authority(self):
        with Session(self.engine) as session:
            return load_authority(session)

    def policy(self, policy: PolicyV1):
        payload = policy.model_dump(mode="json")
        with Session(self.engine) as session, session.begin():
            row = session.get(PolicySnapshot, policy.version)
            if row is None:
                session.add(PolicySnapshot(version=policy.version, payload=payload))
            elif row.payload != payload:
                raise ValueError("Immutable policy version conflict")
        return policy

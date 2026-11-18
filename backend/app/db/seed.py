"""Insert missing synthetic records; reject drift, never rewrite authority."""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.contracts import VendorV1, PurchaseOrderV1, PriorBilledInvoiceV1
from .models import Vendor, PurchaseOrder, POLine, PriorBilledInvoice
from .session import create_db_engine, initialize

MANIFEST = Path(__file__).resolve().parents[3] / "data/seed_manifest.json"

def seed(engine, manifest_path=MANIFEST):
    source = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    vendors = [VendorV1.model_validate(v) for v in source["vendors"]]
    pos = [PurchaseOrderV1.model_validate(p) for p in source["purchase_orders"]]
    billed = [PriorBilledInvoiceV1.model_validate(b) for b in source["prior_billed_invoices"]]
    def insert_or_verify(session, model, key, **values):
        current = session.get(model, key)
        if current is None:
            session.add(model(id=key, **values))
        elif any(getattr(current, name) != value for name, value in values.items()):
            raise ValueError(f"Authoritative seed drift: {model.__tablename__}/{key}; nothing overwritten")
    with Session(engine) as session, session.begin():
        for v in vendors:
            insert_or_verify(session, Vendor, v.id, payload=v.model_dump(mode="json"))
        session.flush()
        for p in pos:
            insert_or_verify(session, PurchaseOrder, p.id, vendor_id=p.vendor_id, authorized_net=p.authorized_net, payload=p.model_dump(mode="json"))
        session.flush()
        for p in pos:
            for line in p.lines:
                insert_or_verify(session, POLine, f"{p.id}:{line.item_code}", po_id=p.id, item_code=line.item_code, ordered_qty=line.ordered_qty, unit_price_net=line.unit_price_net, authorized_net=line.authorized_net)
        for b in billed:
            insert_or_verify(session, PriorBilledInvoice, b.id, vendor_id=b.vendor_id, po_id=b.po_id, net=b.net, payload=b.model_dump(mode="json"))
    return {"vendors": len(vendors), "purchase_orders": len(pos), "prior_billed_invoices": len(billed)}

def main():
    engine = create_db_engine()
    try:
        initialize(engine)
        print(json.dumps(seed(engine), sort_keys=True))
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()

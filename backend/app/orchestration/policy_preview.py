"""Read-only simulation coordination. Financial rules stay in the existing domain."""
from hashlib import sha256
import json

from app.contracts import PolicyV1
from app.domain import build_context, evaluate


class PreviewUnavailable(ValueError):
    pass


def preview(snapshot, repository, tolerance):
    if (snapshot.execution_state != 'COMPLETED' or snapshot.extracted_invoice is None
            or snapshot.decision is None or snapshot.policy_snapshot is None):
        raise PreviewUnavailable('A completed business analysis is required')
    # Copy every other recorded control, including the explicit-PO and hard ceiling settings.
    payload = snapshot.policy_snapshot.model_dump(mode='json')
    payload['price_tolerance_pct'] = str(tolerance)
    identity = sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    payload['version'] = 'preview-' + identity
    policy = PolicyV1.model_validate(payload)
    context = build_context(snapshot.extracted_invoice, *repository.authority())
    decision = evaluate(context, policy)
    # Policy identity necessarily differs; changed means the business result differs.
    changed = (decision.model_dump(exclude={'policy_version'}) !=
               snapshot.decision.model_dump(exclude={'policy_version'}))
    return policy, decision, changed

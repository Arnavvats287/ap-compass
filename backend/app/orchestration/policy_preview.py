"""Read-only simulation coordination. Financial rules stay in the existing domain."""
from app.domain import build_context, evaluate
from app.domain.decisions import preserve_submission_finding
from .policies import with_price_tolerance


class PreviewUnavailable(ValueError):
    pass


def preview(snapshot, repository, tolerance):
    if (snapshot.execution_state != 'COMPLETED' or snapshot.extracted_invoice is None
            or snapshot.decision is None or snapshot.policy_snapshot is None):
        raise PreviewUnavailable('A completed business analysis is required')
    # Copy every other recorded control, including the explicit-PO and hard ceiling settings.
    policy = with_price_tolerance(snapshot.policy_snapshot, tolerance, "preview")
    context = build_context(snapshot.extracted_invoice, *repository.authority())
    decision = preserve_submission_finding(evaluate(context, policy), snapshot.decision, policy)
    # Policy identity necessarily differs; changed means the business result differs.
    changed = (decision.model_dump(exclude={'policy_version'}) !=
               snapshot.decision.model_dump(exclude={'policy_version'}))
    return policy, decision, changed

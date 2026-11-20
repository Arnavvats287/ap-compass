"""Build immutable variants of an existing policy without changing its other controls."""
from hashlib import sha256
import json

from app.contracts import PolicyV1


def with_price_tolerance(base, tolerance, namespace):
    payload = base.model_dump(mode="json")
    payload["price_tolerance_pct"] = str(tolerance)
    identity = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    payload["version"] = f"{namespace}-{identity}"
    return PolicyV1.model_validate(payload)

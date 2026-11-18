"""Public pure-engine entry points. Trusted snapshot loading is a caller concern."""
from .decisions import evaluate
from .matching import build_context, resolve_vendor

__all__ = ["evaluate", "build_context", "resolve_vendor"]

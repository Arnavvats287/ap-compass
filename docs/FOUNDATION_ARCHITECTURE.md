# Phase 1 architecture and contract mapping

The initial implementation follows `CONTRACTS.md`; there are no financial policy or seed changes.
The Phase 1 user request explicitly authorizes the initial typed contracts and database schema.
No earlier application code existed. Existing accepted ADRs remain unchanged; no new ADR is required.

## Boundaries

- `app/contracts`: frozen Pydantic snapshots, immutable tuple collections, nullable source facts.
- `app/db`: SQLAlchemy models, initial schema, SQLite engine and transactional idempotent seed loader.
- `app/api`: health only. Routes contain no business rules.
- `app/documents` and `app/ai`: Phase 3 boundaries only; no provider calls.
- `app/domain/matching.py`: PO identity boundary, independent of eligibility.
- `app/domain/rules.py` and `decisions.py`: pure rule/evaluation boundaries for Phase 2; no engines yet.
- `app/orchestration`: Phase 4 boundary only. No fake progress or invented runs.

## Concrete v1 representations

The specification defines conceptual fields; the following explicit mappings are additive/minimal adaptations:

- Extraction: `vendor_name_raw`, `vendor_name_normalized`, `net`, `tax`, `total`; `total` is the document's gross.
  Unknown fields default to null. Lines use `qty`, `unit_price_net`, `net`; evidence uses a typed tuple keyed by `field`.
- Evidence: `route` uses `native_text|image_only|mixed`; `raw_value`, `normalized_value`, page/quote and state retained.
  A state label does not implement source verification; actual verification is Phase 3.
- Procurement/history: typed snapshots mirror the seed manifest without changing values or business behavior.
- Context: full PO candidates include selection provenance and optional integer rank; full authoritative snapshots
  are passed independently of any future financial eligibility evaluation. No fuzzy matching is implemented.
- Finding: `values` is an immutable tuple of named string/nullable values, preserving exact decimal display values.
  Reason codes are open strings to allow new rules. No finding catalog or precedence is implemented.
- Policy: fixed initial effective timestamp and version, Decimal 0.02/1.00/0.00 defaults. Snapshots frozen.
- Run: explicit timing entries, nullable usage counters, model/schema metadata, embedded immutable policy snapshot.
  COMPLETED requires a decision with matching policy; every other execution state forbids a decision.
- `InvoiceRun`, `RunStage`, `PolicySnapshot` have minimal separate tables and versioned JSON payloads.
  Authoritative Vendor/PO/line/history tables have no analysis lifecycle hooks or cascading analysis relationships.
  Future persistence APIs must validate the corresponding contracts; Phase 1 does not expose write routes.

## Financial storage

Python uses finite Decimal values and rejects float/bool monetary inputs. SQLite NUMERIC affinity could
round through binary floats, so dedicated financial columns use a Decimal-to-TEXT SQLAlchemy type.
JSON snapshots use Pydantic's decimal-string serialization. Quantities also retain exact decimal precision.
No SQL SUM is used on decimal text. Future evaluators receive Decimal typed snapshots.
No unknown invoice amount is defaulted to zero; zero in test sum accumulators represents an empty known ledger.

## Seed and schema lifecycle

The seed loader validates complete source records, inserts missing rows in one transaction, compares existing
rows exactly, and raises on drift without rewriting authoritative records. No reset/delete command exists.
Initial schema uses `create_all`; existing tables are not dropped. Additive migrations are required before
changing a persisted schema in a later phase. Tests isolate DB files and compare all authoritative rows before
and after run insert/update/delete. This proves current lifecycle separation, not future code correctness.

## Reference conflicts resolved by scope

The old starter README proposes creating a repo, a `segment-01-foundation` checkpoint and early deployment.
The current user says reuse the existing repo, use `phase-01-foundation`, and keep Docker optional/local first.
The current request takes precedence. The supplied seven-page official Zamp brief was read from
`C:/Users/Asus/Downloads/asa-case-study.pdf`; it supports PS-1 and synthetic test inputs. Its later live workflow,
dashboard, edge-case and demo-video deliverables do not expand Phase 1. No official PDF is copied into the public repo.
The brief's FAQ permits a simple presentation while page 2 explicitly values an intuitive UI/live stages/dashboard;
our accepted UI direction satisfies the stronger requirement in later phases.

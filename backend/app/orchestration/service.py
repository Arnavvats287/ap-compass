"""Coordinate existing adapters and pure engine; no financial or matching rules."""
import asyncio
import logging
from hashlib import sha256
from time import perf_counter

from app.contracts import EXECUTION_ERROR_CODES, PolicyV1, TimingV1, UsageV1
from app.documents.types import ExtractionError
from app.domain import build_context, evaluate
from app.domain.controls import submitted_duplicate
from app.domain.decisions import aggregate
from .policies import with_price_tolerance

logger = logging.getLogger(__name__)


def usage_snapshot(calls, attempts):
    def tokens(name):
        values = [getattr(attempt.usage, name) for attempt in attempts if attempt.inference_called]
        return sum(values) if values and all(value is not None for value in values) else None
    return UsageV1(model_calls=calls, input_tokens=tokens("input_tokens"), output_tokens=tokens("output_tokens"))


class RunService:
    def __init__(self, repository, documents, extractor, policy=None, *, uploads_enabled=True, capacity=3):
        self.repository, self.documents, self.extractor = repository, documents, extractor
        self.current_policy = policy or PolicyV1()
        self.semaphore = asyncio.Semaphore(1)
        self.tasks = set()
        self.uploads_enabled = uploads_enabled
        self.capacity = capacity
        self.admitted = 0

    def reserve_upload(self):
        # Reservation, transfer and release all happen on the application's event loop.
        if self.admitted >= self.capacity:
            return False
        self.admitted += 1
        return True

    def release_upload(self):
        self.admitted -= 1

    def submit_upload(self, raw, tolerance=None):
        """Transfer one existing admission slot to the background workflow."""
        policy = self.current_policy
        if tolerance is not None and tolerance != policy.price_tolerance_pct:
            policy = with_price_tolerance(policy, tolerance, "intake")
        ready = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(self.accept_and_process(raw, ready, policy))
        self.tasks.add(task)

        def finished(done):
            self.tasks.discard(done)
            self.release_upload()
            if not ready.done():
                ready.set_result(None)
            if not done.cancelled() and done.exception() is not None:
                # Persistence itself may be unavailable; never emit exception payloads.
                logger.error("stage=persistence error=INTERNAL_ERROR")
        task.add_done_callback(finished)
        return ready

    def store_run(self, raw, policy):
        document_id = self.documents.write(raw)
        try:
            snapshot = self.repository.create(document_id, policy_snapshot=policy,
                                              document_sha256=sha256(raw).hexdigest())
        except Exception:
            try:
                self.documents.discard_uncommitted(document_id)
            except OSError:
                logger.error("stage=upload_cleanup error=DOCUMENT_CLEANUP_FAILED")
            raise
        reused = snapshot.document_id != document_id
        if reused:
            try:
                self.documents.discard_uncommitted(document_id)
            except OSError:
                logger.error("stage=upload_cleanup error=DOCUMENT_CLEANUP_FAILED")
        return snapshot, reused

    async def accept_and_process(self, raw, ready, policy):
        persistence = asyncio.create_task(asyncio.to_thread(self.store_run, raw, policy))
        try:
            snapshot, reused = await asyncio.shield(persistence)
        except asyncio.CancelledError:
            # Let the file/DB pair settle before disposal. Startup will interrupt any queued row.
            await asyncio.gather(persistence, return_exceptions=True)
            raise
        except Exception:
            logger.error("stage=upload_persistence error=UPLOAD_STORAGE_UNAVAILABLE")
            ready.set_result(None)
            return
        ready.set_result((snapshot, reused))
        if not reused:
            await self.process(snapshot.id)

    async def close(self):
        pending = tuple(self.tasks)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    async def idle(self):
        """Synchronization hook for shutdown/tests, not a polling timer."""
        await asyncio.gather(*tuple(self.tasks))

    async def process(self, run_id):
        async with self.semaphore:
            snapshot = self.repository.load(run_id)
            if snapshot is None or snapshot.execution_state != "QUEUED":
                return
            start = perf_counter()
            active = "extracting_invoice"
            timings = []
            began = start
            try:
                self.repository.update(run_id, execution_state="RUNNING", stages={active: "RUNNING"})
                began = perf_counter()
                raw = await asyncio.to_thread(self.documents.read, snapshot.document_id)
                result = await self.extractor(raw)
                timings.append(TimingV1(name="extraction", milliseconds=int((perf_counter()-began)*1000)))
                metadata = result.metadata
                usage = usage_snapshot(metadata.model_calls, metadata.attempts)
                self.repository.update(run_id, extracted_invoice=result.invoice, source_route=metadata.route,
                    model_id=next((attempt.actual_model_id for attempt in reversed(metadata.attempts)
                                   if attempt.requested_model_id == metadata.selected_model_id
                                   and attempt.error_code is None and attempt.actual_model_id), metadata.selected_model_id),
                    extraction_schema_version=metadata.schema_version,
                    usage=usage, timings=tuple(timings), stages={active: "PASSED", "matching_records": "RUNNING"})
                active = "matching_records"
                began = perf_counter()
                vendors, pos, history = self.repository.authority()
                context = build_context(result.invoice, vendors, pos, history)
                timings.append(TimingV1(name="matching", milliseconds=int((perf_counter()-began)*1000)))
                self.repository.update(run_id, candidates=context.candidates, timings=tuple(timings),
                    stages={active: "PASSED", "evaluating_controls": "RUNNING"})
                active = "evaluating_controls"
                began = perf_counter()
                policy = self.repository.policy(snapshot.policy_snapshot or self.current_policy)
                decision = evaluate(context, policy)
                prior_id = self.repository.prior_verified_submission(run_id, context.canonical_vendor,
                                                                     context.invoice, vendors)
                if prior_id is not None:
                    decision = aggregate((*decision.findings, submitted_duplicate(prior_id)), policy)
                timings.append(TimingV1(name="evaluation", milliseconds=int((perf_counter()-began)*1000)))
                self.repository.update(run_id, policy_snapshot=policy, timings=tuple(timings),
                    stages={active: "PASSED", "finalizing": "RUNNING"})
                active = "finalizing"
                began = perf_counter()
                timings.append(TimingV1(name="total_processing", milliseconds=int((perf_counter()-start)*1000)))
                self.repository.update(run_id, execution_state="COMPLETED", decision=decision,
                    execution_error_code=None, timings=tuple(timings), stages={active: "PASSED"})
            except asyncio.CancelledError:
                # No automatic replay: next startup reconciles persisted work as INTERRUPTED.
                raise
            except Exception as error:
                code = error.code if isinstance(error, ExtractionError) and error.code in EXECUTION_ERROR_CODES else "INTERNAL_ERROR"
                name = {"extracting_invoice": "extraction", "matching_records": "matching",
                        "evaluating_controls": "evaluation", "finalizing": "finalizing"}[active]
                if not any(timing.name == name for timing in timings):
                    timings.append(TimingV1(name=name, milliseconds=int((perf_counter()-began)*1000)))
                timings.append(TimingV1(name="total_processing", milliseconds=int((perf_counter()-start)*1000)))
                changes = {"timings": tuple(timings)}
                if isinstance(error, ExtractionError):
                    changes["usage"] = usage_snapshot(error.calls, error.attempts)
                self.repository.update(run_id, **changes)
                self.repository.terminate(run_id, code)
                provider_http_status = error.provider_status if isinstance(error, ExtractionError) else None
                logger.warning("run=%s stage=%s error=%s elapsed_ms=%d provider_http_status=%s",
                               run_id, active, code, timings[-1].milliseconds,
                               provider_http_status if type(provider_http_status) is int
                               and 100 <= provider_http_status <= 599 else None)

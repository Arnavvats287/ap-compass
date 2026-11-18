"""Coordinate existing adapters and pure engine; no financial or matching rules."""
import asyncio
import logging
from time import perf_counter

from app.contracts import EXECUTION_ERROR_CODES, PolicyV1, TimingV1, UsageV1
from app.documents.types import ExtractionError
from app.domain import build_context, evaluate

logger = logging.getLogger(__name__)


def usage_snapshot(calls, attempts):
    def tokens(name):
        values = [getattr(attempt.usage, name) for attempt in attempts if attempt.inference_called]
        return sum(values) if values and all(value is not None for value in values) else None
    return UsageV1(model_calls=calls, input_tokens=tokens("input_tokens"), output_tokens=tokens("output_tokens"))


class RunService:
    def __init__(self, repository, documents, extractor, policy=None):
        self.repository, self.documents, self.extractor = repository, documents, extractor
        self.current_policy = policy or PolicyV1()
        self.semaphore = asyncio.Semaphore(1)
        self.tasks = set()

    def submit(self, run_id):
        task = asyncio.create_task(self.process(run_id))
        self.tasks.add(task)
        def finished(done):
            self.tasks.discard(done)
            if not done.cancelled() and done.exception() is not None:
                # Persistence itself may be unavailable; never emit exception payloads.
                logger.error("run=%s stage=persistence error=INTERNAL_ERROR", run_id)
        task.add_done_callback(finished)

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

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
                policy = self.repository.policy(self.current_policy)
                decision = evaluate(context, policy)
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
                logger.warning("run=%s stage=%s error=%s", run_id, active, code)

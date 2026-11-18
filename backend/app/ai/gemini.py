"""Official Google GenAI SDK adapter, fixed endpoint and no tool authority."""
import asyncio
from dataclasses import dataclass, field
import json
import os
import re

from google import genai
from google.genai import errors, types
import httpx2

from app.documents.schema import provider_schema
from app.documents.types import DocumentInspection, ExtractionError, ProviderReply, TokenUsage
from .provider import SYSTEM_INSTRUCTION, mark_inference_called


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str = field(repr=False)
    primary_model: str = "gemini-3.5-flash-lite"
    escalation_model: str = "gemini-3.6-flash"
    scan_model: str | None = None
    escalation_thinking_level: str = "MINIMAL"
    escalation_enabled: bool = False

    @property
    def active_models(self):
        models = (self.primary_model, self.escalation_model) if self.escalation_enabled else (self.primary_model,)
        return tuple(dict.fromkeys(models))

    @classmethod
    def from_environment(cls):
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key or key.startswith("replace_"):
            raise ExtractionError("CONFIGURATION")
        enabled = os.getenv("GEMINI_ESCALATION_ENABLED", "false").strip().casefold()
        if enabled not in ("true", "false"):
            raise ExtractionError("CONFIGURATION")
        primary = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite")
        settings = cls(
            api_key=key, primary_model=primary,
            escalation_model=os.getenv("GEMINI_ESCALATION_MODEL", "gemini-3.6-flash"),
            scan_model=(os.getenv("GEMINI_SCAN_MODEL") or None) if enabled == "true" else primary,
            escalation_thinking_level=os.getenv("GEMINI_ESCALATION_THINKING_LEVEL", "MINIMAL").upper(),
            escalation_enabled=enabled == "true",
        )
        if any(not re.fullmatch(r"gemini-[a-z0-9.\-]{1,80}", model) for model in settings.active_models):
            raise ExtractionError("CONFIGURATION")
        if settings.escalation_enabled and settings.scan_model and settings.scan_model not in settings.active_models:
            raise ExtractionError("CONFIGURATION")  # Exactly two configured models, never a third.
        if settings.escalation_enabled and settings.escalation_thinking_level not in ("MINIMAL", "LOW", "MEDIUM", "HIGH"):
            raise ExtractionError("CONFIGURATION")
        return settings


def make_client(settings: GeminiSettings):
    return genai.Client(
        api_key=settings.api_key, enterprise=False, vertexai=False,
        http_options=types.HttpOptions(
            base_url="https://generativelanguage.googleapis.com", api_version="v1beta",
            timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def provider_error(error):
    code = getattr(error, "code", None)
    if code in (401, 403):
        return ExtractionError("AUTHORIZATION", provider_status=code)
    if code == 404:
        return ExtractionError("MODEL_UNAVAILABLE", provider_status=code)
    if code == 429:
        return ExtractionError("RATE_LIMIT", provider_status=code)  # Never hide exhaustion by switching quota.
    if code in (500, 502, 503, 504):
        return ExtractionError("PROVIDER_UNAVAILABLE", retryable=True, provider_status=code)
    return ExtractionError("PROVIDER_REJECTED", provider_status=code if isinstance(code, int) else None)


async def verify_model(client, model_id):
    try:
        info = await asyncio.wait_for(client.aio.models.get(model=model_id), 15)
    except errors.APIError as error:
        raise provider_error(error) from None
    except (TimeoutError, httpx2.TimeoutException):
        raise ExtractionError("PROVIDER_TIMEOUT") from None
    except httpx2.TransportError:
        raise ExtractionError("PROVIDER_UNAVAILABLE") from None
    except Exception:
        raise ExtractionError("PROVIDER_REJECTED") from None
    if "generateContent" not in (info.supported_actions or ()):
        raise ExtractionError("MODEL_UNAVAILABLE")
    return {"requested_model": model_id, "resource_name": info.name, "version": info.version,
            "supported_actions": info.supported_actions}


class GeminiProvider:
    def __init__(self, client, model_id, *, thinking_level=None, verify_access=False):
        self._client = client
        self.model_id = model_id
        self.thinking_level = thinking_level
        self._verify_access = verify_access

    async def generate(self, document: DocumentInspection, timeout_seconds: float) -> ProviderReply:
        mark_inference_called(False)
        if self._verify_access:
            try:
                # Reserve time for generation and classify metadata-only timeout
                # before the pipeline's whole-attempt deadline can expire.
                await asyncio.wait_for(verify_model(self._client, self.model_id),
                                       min(15, timeout_seconds / 2))
            except TimeoutError:
                raise ExtractionError("PROVIDER_TIMEOUT", inference_attempted=False) from None
            except ExtractionError as error:
                raise ExtractionError(error.code, retryable=error.retryable, provider_status=error.provider_status,
                                      inference_attempted=False) from None
            self._verify_access = False
        parts = []
        for page in document.pages:
            parts.append(types.Part.from_text(text=json.dumps({
                "original_pdf_page": page.number, "route": page.route,
                "untrusted_native_text": page.native_text if page.route == "native_text" else None,
            })))
            if page.image_png is not None:
                parts.append(types.Part.from_bytes(data=page.image_png, mime_type="image/png"))
        try:
            mark_inference_called(True)
            response = await self._client.aio.models.generate_content(
                model=self.model_id, contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION, response_mime_type="application/json",
                    response_json_schema=provider_schema(), temperature=0,
                    thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level) if self.thinking_level else None,
                    max_output_tokens=12_000, tools=[],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000),
                                                   retry_options=types.HttpRetryOptions(attempts=1)),
                ),
            )
        except errors.APIError as error:
            raise provider_error(error) from None
        except (TimeoutError, httpx2.TimeoutException):
            raise ExtractionError("PROVIDER_TIMEOUT", retryable=True) from None
        except httpx2.TransportError:
            raise ExtractionError("PROVIDER_UNAVAILABLE", retryable=True) from None
        except Exception:
            raise ExtractionError("PROVIDER_REJECTED") from None
        usage = response.usage_metadata
        tokens = TokenUsage(
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            thinking_tokens=getattr(usage, "thoughts_token_count", None),
            total_tokens=getattr(usage, "total_token_count", None),
        )
        # Never invoke or interpret any returned function/tool request.
        if any(getattr(part, "function_call", None) for candidate in (response.candidates or ())
               for part in (getattr(candidate.content, "parts", None) or ())):
            raise ExtractionError("PROVIDER_REJECTED")
        return ProviderReply(response.text or "", getattr(response, "model_version", None), tokens)


async def extract_configured_pdf(raw: bytes, *, max_attempts: int = 2):
    """Standalone primary adapter with explicitly enabled, optional escalation.

    Environment loading is explicit at the development command/caller boundary.
    Model metadata checks establish availability of the requested API action;
    actual generation errors still propagate as technical failures.
    """
    from app.documents.pipeline import extract_pdf
    settings = GeminiSettings.from_environment()
    client = make_client(settings)
    try:
        await verify_model(client, settings.primary_model)
        primary = GeminiProvider(client, settings.primary_model)
        stronger = None
        if settings.escalation_enabled:
            # Check optional metadata only if this provider is actually needed.
            # Failure then preserves an already usable primary via the pipeline.
            stronger = GeminiProvider(client, settings.escalation_model,
                                      thinking_level=settings.escalation_thinking_level, verify_access=True)
        scan = stronger if stronger and settings.scan_model == stronger.model_id else primary
        return await extract_pdf(raw, primary, escalation_provider=stronger, scan_provider=scan,
                                 max_attempts=max_attempts)
    finally:
        await client.aio.aclose()
        client.close()

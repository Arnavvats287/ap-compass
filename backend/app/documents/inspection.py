"""Byte validation and bounded, nonpersistent PyMuPDF subprocess inspection."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

from .limits import MAX_INPUT_BYTES, PARSER_TIMEOUT_SECONDS
from .types import DocumentInspection, ExtractionError, PageInspection


def inspect_pdf(raw: bytes) -> DocumentInspection:
    if not isinstance(raw, bytes) or not raw:
        raise ExtractionError("EMPTY_PDF")
    if len(raw) > MAX_INPUT_BYTES:
        raise ExtractionError("INPUT_TOO_LARGE")
    if not raw.startswith(b"%PDF-") or not raw.rstrip().endswith(b"%%EOF"):
        raise ExtractionError("INVALID_PDF")
    # Parser receives no key, bank environment, model config or user-selected executable.
    environment = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH") if k in os.environ}
    environment.update(PYTHONPATH=str(Path(__file__).resolve().parents[2]), PYTHONIOENCODING="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "app.documents._parse_process"], input=raw,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=PARSER_TIMEOUT_SECONDS,
            env=environment, shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        raise ExtractionError("PARSER_TIMEOUT") from None
    except OSError:
        raise ExtractionError("PARSER_FAILED") from None
    if completed.returncode or len(completed.stdout) > 20 * 1024 * 1024:
        raise ExtractionError("PARSER_FAILED")
    try:
        data = json.loads(completed.stdout)
        if "error" in data:
            allowed = {"INVALID_PDF", "EMPTY_PDF", "ENCRYPTED_PDF", "UNSUPPORTED_PDF", "PAGE_LIMIT", "RESOURCE_LIMIT", "PARSER_FAILED"}
            raise ExtractionError(data["error"] if data["error"] in allowed else "PARSER_FAILED")
        result = data["result"]
        pages = tuple(PageInspection(**{**p, "lines": tuple(tuple(line) for line in p["lines"]),
                                       "line_rects": tuple(tuple(rect) if rect is not None else None
                                                           for rect in p.get("line_rects", ())),
                                       "image_png": base64.b64decode(p["image_png"]) if p["image_png"] else None})
                      for p in result["pages"])
        return DocumentInspection(route=result["route"], pages=pages, byte_count=result["byte_count"])
    except (ValueError, KeyError, TypeError):
        raise ExtractionError("PARSER_FAILED") from None

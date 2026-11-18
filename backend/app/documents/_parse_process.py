"""Short-lived parser sandbox. Fixed code; input is PDF bytes, never commands."""
import base64
import json
import math
import sys

from .limits import (
    MAX_IMAGE_EDGE, MAX_IMAGE_PIXELS, MAX_IMAGES_BYTES, MAX_INPUT_BYTES,
    MAX_PAGE_CHARS, MAX_PAGES, MAX_TOTAL_CHARS, constrain_process_memory,
)
from .types import ExtractionError


def inspect(raw):
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    try:
        pdf = pymupdf.open(stream=raw, filetype="pdf")
    except Exception:
        raise ExtractionError("INVALID_PDF") from None
    with pdf:
        if not pdf.is_pdf or pdf.is_repaired:
            raise ExtractionError("INVALID_PDF")
        if pdf.needs_pass or pdf.is_encrypted or pdf.xref_get_key(-1, "Encrypt")[0] != "null":
            raise ExtractionError("ENCRYPTED_PDF")
        if pdf.embfile_count() or pdf.xref_get_key(pdf.pdf_catalog(), "AcroForm/XFA")[0] != "null":
            raise ExtractionError("UNSUPPORTED_PDF")
        if not len(pdf):
            raise ExtractionError("EMPTY_PDF")
        if len(pdf) > MAX_PAGES:
            raise ExtractionError("PAGE_LIMIT")
        pages, chars, image_bytes, has_content = [], 0, 0, False
        for index, page in enumerate(pdf):
            width, height = page.rect.width, page.rect.height
            if not (math.isfinite(width) and math.isfinite(height) and 1 <= width <= 14400 and 1 <= height <= 14400):
                raise ExtractionError("RESOURCE_LIMIT")
            text = page.get_text("text", sort=True)
            chars += len(text)
            if len(text) > MAX_PAGE_CHARS or chars > MAX_TOTAL_CHARS:
                raise ExtractionError("RESOURCE_LIMIT")
            # Text-only flags avoid decompressing embedded raster images into the text dict.
            blocks = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT, sort=True)["blocks"]
            lines = [["".join(s["text"] for s in line["spans"]), max((s["size"] for s in line["spans"]), default=0)]
                     for block in blocks if block["type"] == 0 for line in block["lines"]]
            if len(lines) > 4000:
                raise ExtractionError("RESOURCE_LIMIT")
            readable = len(text.strip()) >= 40 and sum(c.isprintable() or c.isspace() for c in text) >= len(text) * .95 and "\ufffd" not in text
            large_image = any(item["bbox"][2] - item["bbox"][0] > width * .7
                              and item["bbox"][3] - item["bbox"][1] > height * .7
                              for item in page.get_image_info())
            route = "mixed" if readable and large_image else "native_text" if readable else "image_only"
            image, iw, ih = None, None, None
            if route != "native_text":
                scale = min(120 / 72, (MAX_IMAGE_EDGE - 2) / max(width, height), math.sqrt(MAX_IMAGE_PIXELS / (width * height)) * .999)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
                iw, ih = pix.width, pix.height
                if iw * ih > MAX_IMAGE_PIXELS or max(iw, ih) > MAX_IMAGE_EDGE:
                    raise ExtractionError("RESOURCE_LIMIT")
                has_content = has_content or not pix.is_unicolor
                image = base64.b64encode(pix.tobytes("png")).decode("ascii")
                image_bytes += len(image)
                if image_bytes > MAX_IMAGES_BYTES:
                    raise ExtractionError("RESOURCE_LIMIT")
            else:
                has_content = True
            pages.append(dict(number=index + 1, route=route, native_text=text, lines=lines,
                              image_png=image, image_width=iw, image_height=ih))
        if not has_content:
            raise ExtractionError("EMPTY_PDF")
        routes = {p["route"] for p in pages}
        route = next(iter(routes)) if len(routes) == 1 else "mixed"
        return dict(route=route, pages=pages, byte_count=len(raw))


def main():
    try:
        job_handle = constrain_process_memory()
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        result = inspect(raw)
        print(json.dumps({"result": result}, ensure_ascii=True))
    except ExtractionError as error:
        print(json.dumps({"error": error.code}))
    except (MemoryError, OverflowError):
        print('{"error":"RESOURCE_LIMIT"}')
    except Exception:
        print('{"error":"PARSER_FAILED"}')


if __name__ == "__main__":
    main()

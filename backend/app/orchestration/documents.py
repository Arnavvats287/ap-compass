"""Opaque local PDF storage. Filenames supplied by clients never enter this module."""
import os
from pathlib import Path
import re
from uuid import uuid4

from app.db.session import ROOT


class DocumentStore:
    def __init__(self, directory=None):
        directory = Path(directory or os.getenv("AP_COMPASS_DOCUMENT_DIR", "runtime/documents"))
        self.directory = (directory if directory.is_absolute() else ROOT / directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, identifier):
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise FileNotFoundError()
        path = self.directory / (identifier + ".pdf")
        if path.is_symlink() or path.resolve().parent != self.directory:
            raise FileNotFoundError()
        return path

    def write(self, raw):
        identifier = uuid4().hex
        target = self.path(identifier)
        temporary = target.with_suffix(".tmp")
        try:
            with temporary.open("xb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return identifier

    def read(self, identifier):
        return self.path(identifier).read_bytes()

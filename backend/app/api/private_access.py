"""Private demo access boundary and per-process admission settings."""
from base64 import b64decode
from binascii import Error
from dataclasses import dataclass, field
import os
import re
from secrets import compare_digest
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse


@dataclass(frozen=True)
class OperatingSettings:
    uploads_enabled: bool
    upload_capacity: int
    origin: str | None = None
    username: bytes = field(default=b"", repr=False)
    password: bytes = field(default=b"", repr=False)

    @classmethod
    def from_environment(cls):
        mode = os.getenv("AP_COMPASS_MODE", "local")
        enabled = os.getenv("AP_COMPASS_UPLOADS_ENABLED", "true" if mode == "local" else "false")
        capacity = os.getenv("AP_COMPASS_UPLOAD_CAPACITY", "3")
        if mode not in {"local", "private"} or enabled not in {"true", "false"} or not re.fullmatch(r"[1-8]", capacity):
            raise RuntimeError("Invalid AP Compass operating mode or upload configuration")
        if mode == "local":
            return cls(enabled == "true", int(capacity))

        origin = os.getenv("AP_COMPASS_PRIVATE_ORIGIN", "")
        username = os.getenv("AP_COMPASS_PRIVATE_USERNAME", "")
        password = os.getenv("AP_COMPASS_PRIVATE_PASSWORD", "")
        if (not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", username)
                or not re.fullmatch(r"[!-~]{24,128}", password)
                or password.casefold().startswith(("replace", "example", "changeme", "placeholder"))):
            raise RuntimeError("Private mode requires valid backend credentials")
        try:
            url = urlsplit(origin)
            port = url.port
        except ValueError:
            raise RuntimeError("Invalid private demo origin") from None
        loopback = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not url.hostname or origin != f"{url.scheme}://{url.netloc}" or url.username is not None
                or not re.fullmatch(r"[a-z0-9.\-:\[\]]+", url.netloc) or url.netloc.endswith(":")
                or port == 0 or (url.scheme, port) in {("https", 443), ("http", 80)}
                or (url.scheme != "https" and not (url.scheme == "http" and loopback))):
            raise RuntimeError("Private demo origin requires HTTPS or an exact loopback HTTP origin")
        return cls(enabled == "true", int(capacity), origin, username.encode("ascii"), password.encode("ascii"))


class PrivateAccess:
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings
        url = urlsplit(settings.origin)
        self.scheme = url.scheme
        self.host = url.netloc

    def authorized(self, headers):
        values = headers.getlist("authorization")
        if len(values) != 1 or len(values[0]) > 512:
            return False
        scheme, _, token = values[0].partition(" ")
        if scheme.lower() != "basic":
            return False
        try:
            username, sep, password = b64decode(token, validate=True).partition(b":")
        except (Error, ValueError):
            return False
        match = compare_digest(username, self.settings.username) & compare_digest(password, self.settings.password)
        return bool(sep and match)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        # No IP-based trust or access exemptions. Never challenge on a wrong transport/host.
        if scope["scheme"] != self.scheme or headers.getlist("host") != [self.host]:
            response = JSONResponse({"detail": "Private demo origin required"}, status_code=403)
        elif not self.authorized(headers):
            response = JSONResponse({"detail": "Authentication required"}, status_code=401,
                                    headers={"WWW-Authenticate": 'Basic realm="AP Compass private demo", charset="UTF-8"'})
        elif scope["method"] not in {"GET", "HEAD", "OPTIONS"} and headers.getlist("origin") != [self.settings.origin]:
            response = JSONResponse({"detail": "Same-origin request required"}, status_code=403)
        else:
            response = self.app

        async def protect(message):
            if message["type"] == "http.response.start":
                output = MutableHeaders(scope=message)
                output["Cache-Control"] = "no-store"
                output.setdefault("Referrer-Policy", "no-referrer")
                output.setdefault("X-Content-Type-Options", "nosniff")
                output.setdefault("X-Frame-Options", "SAMEORIGIN")
                output.setdefault("Content-Security-Policy", "frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
            await send(message)

        await response(scope, receive, protect)

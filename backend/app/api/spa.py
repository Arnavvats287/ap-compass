"""Serve the React entry point for known deep-link route shapes."""
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class AppStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            parts = path.replace("\\", "/").strip("/").split("/")
            is_app_route = parts in (["runs"], ["overview"]) or (
                len(parts) == 2 and parts[0] == "runs" and parts[1] not in (".", ".."))
            if error.status_code == 404 and scope["method"] in ("GET", "HEAD") and is_app_route:
                return await super().get_response("index.html", scope)
            raise

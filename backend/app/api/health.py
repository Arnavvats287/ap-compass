from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(prefix="/api")

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str

@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    with request.app.state.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return HealthResponse(status="ok", service="ap-compass", version="0.1.0", database="ok")

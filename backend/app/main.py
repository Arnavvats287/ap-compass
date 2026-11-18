from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api.health import router
from .db.session import create_db_engine, initialize, ROOT
from .db.seed import seed
from .api.runs import router as runs_router
from .ai.gemini import extract_runtime_pdf
from .orchestration.documents import DocumentStore
from .orchestration.repository import RunRepository
from .orchestration.service import RunService

def create_app(db_path=None, *, document_dir=None, extractor=None):
    @asynccontextmanager
    async def lifespan(app):
        engine = create_db_engine(db_path)
        app.state.engine = engine
        service = None
        try:
            initialize(engine)
            seed(engine)
            repository = RunRepository(engine)
            repository.reconcile()
            service = RunService(repository, DocumentStore(document_dir), extractor or extract_runtime_pdf)
            app.state.runs = service
            yield
        finally:
            if service is not None:
                await service.close()
            engine.dispose()
    application = FastAPI(title="AP Compass", version="0.1.0", lifespan=lifespan)
    application.include_router(router)
    application.include_router(runs_router)
    static = ROOT / "frontend/dist"
    if static.is_dir():
        application.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return application

app = create_app()

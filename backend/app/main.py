from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api.health import router
from .api.private_access import OperatingSettings, PrivateAccess
from .db.instance import own_database
from .db.session import create_db_engine, database_path, initialize, ROOT
from .db.seed import seed
from .api.runs import router as runs_router
from .api.policy_preview import router as policy_preview_router
from .api.reviews import router as reviews_router
from .api.exports import router as exports_router
from .api.spa import AppStaticFiles
from .ai.gemini import extract_runtime_pdf
from .orchestration.documents import DocumentStore
from .orchestration.repository import RunRepository
from .orchestration.service import RunService

def create_app(db_path=None, *, document_dir=None, extractor=None):
    settings = OperatingSettings.from_environment()

    @asynccontextmanager
    async def lifespan(app):
        path = database_path(db_path)
        with own_database(path):
            engine = create_db_engine(path)
            app.state.engine = engine
            service = None
            try:
                initialize(engine)
                seed(engine)
                repository = RunRepository(engine)
                repository.reconcile()
                service = RunService(repository, DocumentStore(document_dir), extractor or extract_runtime_pdf,
                                     uploads_enabled=settings.uploads_enabled, capacity=settings.upload_capacity)
                app.state.runs = service
                yield
            finally:
                try:
                    if service is not None:
                        await service.close()
                finally:
                    engine.dispose()
    application = FastAPI(title="AP Compass", version="0.1.0", lifespan=lifespan)
    if settings.origin:
        application.add_middleware(PrivateAccess, settings=settings)
    application.include_router(router)
    application.include_router(runs_router)
    application.include_router(policy_preview_router)
    application.include_router(reviews_router)
    application.include_router(exports_router)
    static = ROOT / "frontend/dist"
    if static.is_dir():
        application.mount("/", AppStaticFiles(directory=static, html=True), name="frontend")
    return application

app = create_app()

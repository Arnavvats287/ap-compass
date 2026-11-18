from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api.health import router
from .db.session import create_db_engine, initialize, ROOT
from .db.seed import seed

def create_app(db_path=None):
    @asynccontextmanager
    async def lifespan(app):
        engine = create_db_engine(db_path)
        app.state.engine = engine
        try:
            initialize(engine)
            seed(engine)
            yield
        finally:
            engine.dispose()
    application = FastAPI(title="AP Compass", version="0.1.0", lifespan=lifespan)
    application.include_router(router)
    static = ROOT / "frontend/dist"
    if static.is_dir():
        application.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return application

app = create_app()

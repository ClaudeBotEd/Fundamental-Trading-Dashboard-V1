from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.config import settings
from core.vault import VaultWriter
from analyzers.ai_analyzer import AIAnalyzer
from api.cache import ResultCache
from api.scheduler import build_scheduler
from api.routes.pairs import router as pairs_router
from api.routes.analyze import router as analyze_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = ResultCache(ttl_seconds=4 * 3600)
    analyzer = AIAnalyzer(settings)
    vault_writer = VaultWriter(settings.obsidian_vault_path)
    scheduler = build_scheduler(analyzer, cache)

    app.state.cache = cache
    app.state.analyzer = analyzer
    app.state.vault_writer = vault_writer
    app.state.scheduler = scheduler

    scheduler.start()
    yield

    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fundamental Trading Dashboard",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(pairs_router)
    app.include_router(analyze_router)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()

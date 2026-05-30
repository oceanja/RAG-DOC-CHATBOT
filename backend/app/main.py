from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models import Project
from app.routers import admin as admin_router
from app.routers import chat as chat_router
from app.routers import projects as projects_router
from app.startup import init_db

WIDGET_BUNDLE = Path(
    settings.widget_bundle_path
    or (Path(__file__).resolve().parents[2] / "widget" / "dist" / "widget.js")
)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    await init_db()
    app_.state.redis_pool = await create_pool(
        RedisSettings.from_dsn(settings.redis_url)
    )
    try:
        yield
    finally:
        await app_.state.redis_pool.aclose()
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # auth is via Bearer header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router.router)
app.include_router(projects_router.router)
app.include_router(chat_router.router)


@app.get("/widget.js")
async def widget_js() -> FileResponse:
    if not WIDGET_BUNDLE.exists():
        raise HTTPException(
            status_code=404,
            detail="Widget bundle not built. Run: cd widget && npm install && npm run build",
        )
    return FileResponse(
        WIDGET_BUNDLE,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/health")
async def health() -> dict[str, object]:
    db_status: str = "ok"
    project_count: int | None = None
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            project_count = await session.scalar(select(func.count()).select_from(Project))
    except Exception as exc:
        db_status = f"error: {exc.__class__.__name__}"

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": db_status,
        "project_count": project_count,
    }

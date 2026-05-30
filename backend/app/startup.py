from sqlalchemy import select, text

from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.models import Project


async def init_db() -> None:
    """Ensure pgvector extension, optionally create tables, seed default project.

    In production set AUTO_CREATE_TABLES=false and manage schema via Alembic
    (`alembic upgrade head`). In dev the create_all path is convenient.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        if settings.auto_create_tables:
            await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Project).limit(1))
        if existing is None:
            session.add(Project(name="Default Project"))
            await session.commit()

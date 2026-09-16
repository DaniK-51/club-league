from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import dispose_engine, get_db
from src.schemas.common import ApiSuccess, HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=ApiSuccess[HealthResponse], tags=["system"])
    async def health(session: AsyncSession = Depends(get_db)) -> ApiSuccess[HealthResponse]:
        try:
            await session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        payload = HealthResponse(status="ok", env=settings.app_env, database=db_status)  # type: ignore[arg-type]
        return ApiSuccess(data=payload)

    return app


app = create_app()

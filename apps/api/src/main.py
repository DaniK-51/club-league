import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.endpoints import admin as admin_endpoints
from src.api.endpoints import auth as auth_endpoints
from src.api.endpoints import moderation as moderation_endpoints
from src.api.endpoints import rating as rating_endpoints
from src.api.endpoints import reports as reports_endpoints
from src.api.endpoints import users as users_endpoints
from src.core.config import get_settings
from src.core.database import dispose_engine, get_db, get_session_factory
from src.core.i18n import normalize_lang, set_request_lang
from src.core.rate_limit import enforce_rate_limit
from src.schemas.common import ApiSuccess, ErrorCode, HealthResponse
from src.services.auto_complete import start_auto_complete_timer, stop_auto_complete_timer
from src.services.violations_service import log_access_violation


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        set_request_lang(normalize_lang(request.headers.get("accept-language")))
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        client = request.client.host if request.client else "unknown"
        try:
            enforce_rate_limit("http", client)
        except Exception as exc:
            # api_error HTTPException
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                detail = exc.detail
                body = detail if isinstance(detail, dict) else {
                    "error": {"code": ErrorCode.RATE_LIMITED, "message": "Too many requests"}
                }
                return JSONResponse(status_code=exc.status_code, content=body)
            raise
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_auto_complete_timer()
    yield
    stop_auto_complete_timer()
    await dispose_engine()


def _error_body(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


_bg_tasks: set[asyncio.Task[Any]] = set()


def _spawn(coro) -> None:  # type: ignore[no-untyped-def]
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Club League 2026 API",
        summary="Reports, moderation, rating and Yandex Disk sync for Innopolis clubs",
        description=(
            "Single source of truth for club activity reports.\n\n"
            "- **Auth**: university SSO (dev: mock-sso). JWT access + refresh.\n"
            "- **Errors**: `{ error: { code, message } }`\n"
            "- **i18n**: `Accept-Language` (en default, ru supported)\n"
            "- **Links only**: no file uploads (domain whitelist)\n"
            "- **Audit**: append-only hash chain\n"
        ),
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "system", "description": "Health and diagnostics"},
            {"name": "auth", "description": "SSO callback, token refresh"},
            {"name": "users", "description": "Current user profile"},
            {"name": "reports", "description": "Report CRUD, submit, comments thread"},
            {"name": "moderation", "description": "Approve / changes / close / dispute / complete / archive"},
            {"name": "admin", "description": "Sudo mode, Yandex sync, rules CRUD, audit"},
            {"name": "rating", "description": "Public club rating"},
            {"name": "criteria", "description": "Active v2 criteria catalog"},
        ],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LanguageMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            body = detail
        else:
            body = _error_body(
                ErrorCode.INTERNAL_SERVER_ERROR,
                detail if isinstance(detail, str) else "Request failed",
            )
        if exc.status_code == 403:
            message = ""
            if isinstance(body.get("error"), dict):
                message = str(body["error"].get("message", ""))
            client = request.client.host if request.client else "unknown"

            async def _log() -> None:
                factory = get_session_factory()
                async with factory() as session:
                    await log_access_violation(
                        session,
                        user_id=None,
                        path=str(request.url.path),
                        method=request.method,
                        detail=f"{client}: {message or 'forbidden'}",
                    )

            _spawn(_log())
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                ErrorCode.VALIDATION_ERROR,
                "; ".join(
                    f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}"
                    for e in exc.errors()
                ),
            ),
        )

    @app.get("/health", response_model=ApiSuccess[HealthResponse], tags=["system"])
    async def health(session: AsyncSession = Depends(get_db)) -> ApiSuccess[HealthResponse]:
        db_status: Literal["ok", "error"]
        try:
            await session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        return ApiSuccess(
            data=HealthResponse(status="ok", env=settings.app_env, database=db_status)
        )

    app.include_router(auth_endpoints.router, prefix=settings.api_prefix)
    app.include_router(users_endpoints.router, prefix=settings.api_prefix)
    app.include_router(reports_endpoints.router, prefix=settings.api_prefix)
    app.include_router(moderation_endpoints.router, prefix=settings.api_prefix)
    app.include_router(admin_endpoints.router, prefix=settings.api_prefix)
    app.include_router(admin_endpoints.criteria_router, prefix=settings.api_prefix)
    app.include_router(rating_endpoints.router, prefix=settings.api_prefix)

    from fastapi.openapi.utils import get_openapi

    def _custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            summary=app.summary,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Access token from POST /api/auth/sso/callback",
        }
        schema.setdefault("security", [{"BearerAuth": []}])
        servers = schema.setdefault("servers", [])
        # Empty URL = same origin (swagger nginx proxies /api → api)
        servers.insert(0, {"url": "", "description": "Same origin (Swagger proxy)"})
        servers.append(
            {
                "url": f"http://127.0.0.1:{settings.api_port}",
                "description": "Direct API",
            }
        )
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()

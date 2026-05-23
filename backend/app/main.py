from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import services
from .database import create_session_factory
from .models import Base
from .routers import auth, certificates, crews, dispatches, jobs, legacy, matching


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "请求参数不正确"
    message = str(errors[0].get("msg") or "请求参数不正确")
    return message.removeprefix("Value error, ")


def create_app(
    database_url: str | None = None,
    create_tables: bool = False,
    seed_demo: bool = False,
) -> FastAPI:
    engine, SessionLocal = create_session_factory(database_url)
    if create_tables:
        Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="出海船员管理系统 API",
        version="2.0.0",
        default_response_class=UTF8JSONResponse,
    )
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        return UTF8JSONResponse(
            status_code=400,
            content={"success": False, "message": _validation_message(exc)},
        )

    @app.exception_handler(services.ApiError)
    async def api_error_handler(request: Request, exc: services.ApiError):
        return UTF8JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message},
        )

    @app.get("/health")
    def health():
        return {"success": True, "message": "FastAPI backend is running"}

    # More specific /api/jobs/{id}/matches routes must be registered before /api/jobs/{id}.
    app.include_router(auth.router)
    app.include_router(crews.router)
    app.include_router(certificates.router)
    app.include_router(matching.router)
    app.include_router(jobs.router)
    app.include_router(dispatches.router)
    app.include_router(legacy.router)

    if seed_demo:
        with SessionLocal() as db:
            services.seed_demo_data(db)

    return app


app = create_app()

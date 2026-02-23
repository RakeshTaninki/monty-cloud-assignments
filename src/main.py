from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.images import router as images_router
from src.core.exceptions import AppError


def create_app() -> FastAPI:
    app = FastAPI(
        title="Secure Image Service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(images_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    return app


app = create_app()

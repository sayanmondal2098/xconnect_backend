import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from platform_services import router
from impl.config import settings
from impl.db.session import init_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("xconnect.api")

app = FastAPI(title=settings.app_name, version="0.1.0")

# CORS (configure in env)
origins = settings.cors_allow_origins_list
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    trace_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.trace_id = trace_id

    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.time() - start) * 1000
        path = request.url.path
        method = request.method
        status_code = response.status_code if response else 500
        client_host = request.client.host if request.client else "-"
        logger.info(
            "trace_id=%s method=%s path=%s status=%s duration_ms=%.2f client=%s",
            trace_id,
            method,
            path,
            status_code,
            duration_ms,
            client_host,
        )
        if response:
            response.headers["x-trace-id"] = trace_id


@app.on_event("startup")
def _startup() -> None:
    init_db()

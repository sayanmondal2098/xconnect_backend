from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from platform_services import router
from impl.config import settings
from impl.db.session import init_db


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


@app.on_event("startup")
def _startup() -> None:
    init_db()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth as auth_router
from app.routers import files as files_router
from app.routers import folders as folders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="LeBox", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(folders_router.router, prefix="/api/folders", tags=["folders"])
app.include_router(files_router.router, prefix="/api/files", tags=["files"])


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "auth_mode": settings.auth_mode}

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from .config import settings
from .database import SessionLocal
from .services.bootstrap import seed_core
from .api.auth import router as auth_router
from .api.platform import router as platform_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        seed_core(db)
    yield

app = FastAPI(title=settings.app_name, version="0.4.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(platform_router)

@app.get("/api/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name, "version": "0.4.1", "environment": settings.environment, "database": "connected"}

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    assets = frontend_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")

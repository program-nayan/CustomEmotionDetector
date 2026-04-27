"""
Main FastAPI application entry point.
Mounts all routers and serves the frontend static files.
"""

import sys
import os

# Ensure the project root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.database import create_db_tables
from api.routes.auth_router import router as auth_router
from api.routes.chat_router import router as chat_router
from api.routes.dashboard_router import router as dashboard_router

from api.core.logger import logger

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Serenity — AI Wellness Assistant",
    description="An emotion-aware mental wellness companion powered by your custom Fusion Prediction Engine.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow frontend dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please check the logs."},
    )

# ─── Database Initialization ──────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    logger.info("Application starting up...")
    create_db_tables()
    logger.info("[OK] Database tables created / verified.")


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(dashboard_router)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    logger.debug("Health check requested.")
    return {"status": "ok", "service": "Serenity Wellness Assistant"}


# ─── Serve Frontend ───────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

if os.path.exists(FRONTEND_DIR):
    # Mount CSS/JS assets
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/login.html", include_in_schema=False)
    def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

    @app.get("/chat.html", include_in_schema=False)
    def serve_chat():
        return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str = ""):
        # Try exact file first
        exact = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(exact):
            return FileResponse(exact)
        # SPA fallback
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

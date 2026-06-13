"""
main.py — Application Entry Point for Healthians AI
FastAPI app initialization, CORS, router registration, and health check.

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.chat import router as chat_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Healthians AI",
    description=(
        "AI-powered assistant for Healthians — India's leading at-home diagnostics provider. "
        "Explains lab reports, books home sample collection, fetches reports, answers FAQs, "
        "and escalates to doctors when needed."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — Allow all origins for development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------
app.include_router(chat_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Health Check & Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — API welcome message."""
    return {
        "service": "Healthians AI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "healthians-ai",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Startup / Shutdown Events
# ---------------------------------------------------------------------------

from database import init_db

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Healthians AI is starting up...")
    await init_db()
    logger.info("💾 Database initialized successfully.")
    logger.info("📄 API docs available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Healthians AI is shutting down...")

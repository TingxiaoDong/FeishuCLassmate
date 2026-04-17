"""
FastAPI Backend Server for Robotics System.

This module provides the main application entry point for the
backend API service that interfaces between clients and the robot control system.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.db.database import init_database
from backend.api import auth, robot, skills, websocket, sessions, monitoring, debug
from backend.api.auth import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_database()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Robotics System API",
    description="Backend API for robot control, skill execution, and world state management",
    version="0.1.0",
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware - restrict origins via environment variable
# Default to localhost for development, configure for production
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


# Include routers
app.include_router(auth.router)
app.include_router(robot.router)
app.include_router(skills.router)
app.include_router(sessions.router)
app.include_router(websocket.router)
app.include_router(monitoring.router)
app.include_router(debug.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "robotics-backend"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Robotics System API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

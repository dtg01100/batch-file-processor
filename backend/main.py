"""
FastAPI backend main application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# These imports will work when installed in Docker
try:
    from backend.core.scheduler import scheduler
except ImportError as e:
    print(f"Import error (expected in Docker): {e}")
    print("This is expected - will work when running in Docker")
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("Starting up...")
    # Initialize database
    from backend.core.database import initialize_database, get_engine
    initialize_database()
    engine = get_engine()
    print(f"Database initialized: {engine.url}")
    # Start scheduler
    scheduler.start()
    print("Scheduler started")
    yield
    # Shutdown
    print("Shutting down...")
    scheduler.shutdown()
    print("Scheduler shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Batch File Processor API",
    description="Web interface for batch file processing with scheduling",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files (React build)
# Try local path first, then Docker path
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if not frontend_dist.exists():
    frontend_dist = Path("/app/frontend/dist")

if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")
    print(f"Serving frontend from: {frontend_dist}")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.running,
    }


# Include routers
try:
    from backend.api import (
        folders,
        settings,
        jobs,
        runs,
        test_connection,
        output_profiles,
        pipelines,
        triggers,
        legacy_import,
    )

    app.include_router(folders.router, prefix="/api/folders", tags=["folders"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(test_connection.router, prefix="/api", tags=["test"])
    app.include_router(
        output_profiles.router, prefix="/api/output-profiles", tags=["output-profiles"]
    )
    app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
    app.include_router(triggers.router, prefix="/api/triggers", tags=["triggers"])
    app.include_router(legacy_import.router, prefix="/api/legacy-import", tags=["legacy-import"])
    # from backend.api import import_db
    # app.include_router(import_db.router, prefix="/api/import", tags=["import"])
except ImportError as e:
    print(f"Failed to import routers: {e}")


# Root endpoint (serve React app)
@app.get("/")
async def root():
    """Root endpoint - serves React app"""
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse

        return FileResponse(str(index_path))
    return {"message": "Batch File Processor API", "docs": "/docs"}


# Run with: uvicorn backend.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

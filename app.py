"""
MemoryOS FastAPI Application
===========================
Simple development application for testing the current setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="MemoryOS API",
    description="Family AI Memory Operating System API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and setup routers
try:
    from api.routers import setup_routers

    setup_routers(app)
except ImportError as e:
    print(f"Warning: Could not import routers: {e}")

    # Add basic health endpoint as fallback
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "memoryos-api"}


@app.get("/")
async def root():
    return {
        "message": "MemoryOS API - Family AI Memory Operating System",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

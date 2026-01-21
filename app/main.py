"""
Main FastAPI application
Platform-agnostic backend for GetStream Activity Feeds
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api import router as api_router

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Platform-agnostic backend API for GetStream Activity Feeds",
    debug=settings.DEBUG
)

# Configure CORS
allowed_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
        "endpoints": {
            "health": "/health",
            "feeds": f"{settings.API_PREFIX}/feeds/{{feed_id}}/activities",
            "recent": f"{settings.API_PREFIX}/activities/recent",
            "filter": f"{settings.API_PREFIX}/activities/filter",
            "stats": f"{settings.API_PREFIX}/feeds/{{feed_id}}/stats",
            "token": f"{settings.API_PREFIX}/token/{{feed_id}}",
            "collections": f"{settings.API_PREFIX}/collections/{{collection_name}}"
        }
    }


# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

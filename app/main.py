"""
Main FastAPI application
Platform-agnostic backend for GetStream Activity Feeds
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
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


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    """Serve index.html"""
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')


# Serve index.html for user routes for testing
@app.get("/user1")
@app.get("/user2")
@app.get("/user3")
async def user_root():
    """Serve index.html for specific users"""
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')


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

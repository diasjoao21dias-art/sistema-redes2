"""FastAPI application factory"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from .routes import auth, hosts, monitoring, alerts, users

def create_app(title: str = "Sistemas Olivium Network Monitor", 
               version: str = "2.1.0") -> FastAPI:
    """Create FastAPI application with all routes and middleware"""
    
    app = FastAPI(
        title=title,
        description="Professional Network Monitoring System with Advanced Features",
        version=version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # CORS middleware - will be configured in main.py
    # Removed from here to avoid duplicate middleware
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logging.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "status_code": 500
            }
        )
    
    # Health check
    @app.get("/api/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "Sistemas Olivium Network Monitor",
            "version": version
        }
    
    # Include routers
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(hosts.router, prefix="/api/hosts", tags=["Host Management"])
    app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["Alert Management"])
    app.include_router(users.router, prefix="/api/users", tags=["User Management"])
    
    return app
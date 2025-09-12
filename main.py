"""Main application entry point - Professional FastAPI + Flask Bridge"""

import os
import sys
import logging
from contextlib import asynccontextmanager

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from src.api.main import create_app
from src.database import init_database, migrate_from_old_database, check_database_health

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Sistemas Olivium Network Monitor v2.1")
    
    # Initialize database
    if not init_database():
        logger.error("❌ Failed to initialize database")
        sys.exit(1)
    
    # Migrate from old system
    migrate_from_old_database()
    
    # Health check
    if not check_database_health():
        logger.error("❌ Database health check failed")
        sys.exit(1)
    
    logger.info("✅ Database initialized successfully")
    logger.info("🌐 API documentation available at: http://localhost:5000/api/docs")
    logger.info("📊 Legacy interface available at: http://localhost:5000/")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Sistemas Olivium Network Monitor")

def create_main_app():
    """Create main application with both FastAPI and legacy support"""
    
    # Create FastAPI app with proper CORS
    fastapi_app = create_app()
    
    # Fix CORS configuration 
    from fastapi.middleware.cors import CORSMiddleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Specific origins
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add lifespan
    fastapi_app.router.lifespan_context = lifespan
    
    # Mount static files
    fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Legacy Flask routes bridge
    @fastapi_app.get("/")
    async def legacy_interface():
        """Serve legacy HTML interface"""
        return FileResponse("templates/index.html")
    
    @fastapi_app.get("/status")
    async def legacy_status():
        """Legacy status endpoint for backward compatibility"""
        from src.services.monitoring import MonitoringService
        from src.models.base import SessionLocal
        from src.models.host import Host, HostHistory
        
        monitoring = MonitoringService()
        results = []
        
        with SessionLocal() as db:
            hosts = db.query(Host).filter(Host.enabled == True).all()
            
            for host in hosts:
                latest = db.query(HostHistory).filter(
                    HostHistory.hostname == host.hostname
                ).order_by(HostHistory.timestamp.desc()).first()
                
                result = {
                    "name": host.hostname,
                    "ip": host.ip_address or host.fallback_ip,
                    "status": latest.status.value if latest else "Unknown",
                    "time_last_checked": latest.timestamp.strftime('%d/%m/%Y %H:%M:%S') if latest else None,
                    "latency_ms": latest.latency_ms if latest else None,
                    "reason": latest.reason if latest else None,
                    "method": "HYBRID"
                }
                results.append(result)
        
        return results
    
    return fastapi_app

# Create the app
app = create_main_app()

if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
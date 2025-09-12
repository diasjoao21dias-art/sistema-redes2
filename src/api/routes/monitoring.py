"""Real-time monitoring API routes"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ...models.base import SessionLocal
from ...models.host import Host, HostHistory, HostStatus
from ...services.monitoring import MonitoringService
from ...auth.middleware import require_auth
import json
import asyncio

router = APIRouter()
monitoring_service = MonitoringService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class HostStatusResponse(BaseModel):
    hostname: str
    display_name: Optional[str]
    ip_address: Optional[str]
    status: str
    last_check: Optional[datetime]
    response_time: Optional[float]
    checks: Dict = {}

class MonitoringStats(BaseModel):
    total_hosts: int
    online_hosts: int
    offline_hosts: int
    warning_hosts: int
    maintenance_hosts: int
    total_checks: int
    success_rate: float
    avg_response_time: float

@router.get("/status", response_model=List[HostStatusResponse])
@require_auth
async def get_monitoring_status(
    group: Optional[str] = None,
    site: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get current monitoring status for all hosts"""
    query = db.query(Host).filter(Host.enabled == True)
    
    if group:
        query = query.filter(Host.group_name == group)
    if site:
        query = query.filter(Host.site == site)
    
    hosts = query.all()
    results = []
    
    for host in hosts:
        # Get latest status from history
        latest = db.query(HostHistory).filter(
            HostHistory.hostname == host.hostname
        ).order_by(HostHistory.timestamp.desc()).first()
        
        if status and latest and latest.status.value != status:
            continue
        
        result = HostStatusResponse(
            hostname=host.hostname,
            display_name=host.display_name,
            ip_address=host.ip_address,
            status=latest.status.value if latest else "Unknown",
            last_check=latest.timestamp if latest else None,
            response_time=latest.latency_ms if latest else None,
            checks={}
        )
        results.append(result)
    
    return results

@router.get("/stats", response_model=MonitoringStats)
@require_auth
async def get_monitoring_stats(db: Session = Depends(get_db)):
    """Get monitoring statistics"""
    hosts = db.query(Host).filter(Host.enabled == True).all()
    total_hosts = len(hosts)
    
    status_counts = {
        'online': 0,
        'offline': 0,
        'warning': 0,
        'maintenance': 0
    }
    
    for host in hosts:
        if host.in_maintenance:
            status_counts['maintenance'] += 1
            continue
            
        latest = db.query(HostHistory).filter(
            HostHistory.hostname == host.hostname
        ).order_by(HostHistory.timestamp.desc()).first()
        
        if latest:
            status = latest.status.value.lower()
            if status == 'online':
                status_counts['online'] += 1
            elif status in ['offline', 'unknown']:
                status_counts['offline'] += 1
            else:
                status_counts['warning'] += 1
        else:
            status_counts['offline'] += 1
    
    # Get service stats
    service_stats = monitoring_service.get_monitoring_stats()
    
    success_rate = 0.0
    if service_stats['total_checks'] > 0:
        success_rate = (service_stats['successful_checks'] / service_stats['total_checks']) * 100
    
    return MonitoringStats(
        total_hosts=total_hosts,
        online_hosts=status_counts['online'],
        offline_hosts=status_counts['offline'],
        warning_hosts=status_counts['warning'],
        maintenance_hosts=status_counts['maintenance'],
        total_checks=service_stats['total_checks'],
        success_rate=success_rate,
        avg_response_time=service_stats['avg_response_time']
    )

@router.get("/history/{hostname}")
@require_auth
async def get_host_monitoring_history(
    hostname: str,
    hours: int = 24,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Get monitoring history for specific host"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    history = db.query(HostHistory).filter(
        HostHistory.hostname == hostname,
        HostHistory.timestamp >= since
    ).order_by(HostHistory.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "timestamp": h.timestamp,
            "status": h.status.value,
            "latency_ms": h.latency_ms,
            "ip": h.ip,
            "check_type": h.check_type.value if h.check_type else None,
            "reason": h.reason
        }
        for h in history
    ]

# WebSocket for real-time monitoring updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove failed connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Send periodic updates
            with SessionLocal() as db:
                hosts = db.query(Host).filter(Host.enabled == True).limit(50).all()
                
                updates = []
                for host in hosts:
                    latest = db.query(HostHistory).filter(
                        HostHistory.hostname == host.hostname
                    ).order_by(HostHistory.timestamp.desc()).first()
                    
                    if latest:
                        updates.append({
                            "hostname": host.hostname,
                            "status": latest.status.value,
                            "latency_ms": latest.latency_ms,
                            "ip": latest.ip,
                            "timestamp": latest.timestamp.isoformat()
                        })
                
                await websocket.send_text(json.dumps({
                    "type": "status_update",
                    "data": updates,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            await asyncio.sleep(5)  # Send updates every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/force-check/{hostname}")
@require_auth
async def force_host_check(hostname: str, db: Session = Depends(get_db)):
    """Force immediate check of specific host"""
    host = db.query(Host).filter(Host.hostname == hostname).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Perform check
    result = monitoring_service.check_host_comprehensive(host)
    monitoring_service.save_check_result(result)
    
    return {
        "message": "Check completed",
        "hostname": hostname,
        "status": result['overall_status'].value,
        "timestamp": result['timestamp']
    }
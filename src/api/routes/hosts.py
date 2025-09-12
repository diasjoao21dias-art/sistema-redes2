"""Host management API routes"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...models.base import SessionLocal
from ...models.host import Host, HostHistory
from ...auth.middleware import require_auth, require_permission

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class HostCreate(BaseModel):
    hostname: str
    display_name: Optional[str] = None
    ip_address: Optional[str] = None
    fallback_ip: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    group_name: Optional[str] = None
    site: Optional[str] = None
    enabled: bool = True

class HostResponse(BaseModel):
    id: int
    hostname: str
    display_name: Optional[str]
    ip_address: Optional[str]
    fallback_ip: Optional[str]
    description: Optional[str]
    tags: Optional[str]
    group_name: Optional[str]
    site: Optional[str]
    enabled: bool
    in_maintenance: bool
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[HostResponse])
@require_auth
async def get_hosts(
    skip: int = 0, 
    limit: int = 100,
    group: Optional[str] = None,
    site: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all hosts with optional filtering"""
    query = db.query(Host)
    
    if group:
        query = query.filter(Host.group_name == group)
    if site:
        query = query.filter(Host.site == site)
    if enabled is not None:
        query = query.filter(Host.enabled == enabled)
    
    hosts = query.offset(skip).limit(limit).all()
    return hosts

@router.post("/", response_model=HostResponse)
@require_permission("edit_hosts")
async def create_host(host: HostCreate, db: Session = Depends(get_db)):
    """Create new host"""
    # Check if hostname already exists
    existing = db.query(Host).filter(Host.hostname == host.hostname).first()
    if existing:
        raise HTTPException(status_code=400, detail="Hostname already exists")
    
    db_host = Host(**host.dict())
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    return db_host

@router.get("/{host_id}", response_model=HostResponse)
@require_auth
async def get_host(host_id: int, db: Session = Depends(get_db)):
    """Get host by ID"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host

@router.put("/{host_id}", response_model=HostResponse)
@require_permission("edit_hosts")
async def update_host(host_id: int, host: HostCreate, db: Session = Depends(get_db)):
    """Update host"""
    db_host = db.query(Host).filter(Host.id == host_id).first()
    if not db_host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    for field, value in host.dict().items():
        setattr(db_host, field, value)
    
    db.commit()
    db.refresh(db_host)
    return db_host

@router.delete("/{host_id}")
@require_permission("edit_hosts")
async def delete_host(host_id: int, db: Session = Depends(get_db)):
    """Delete host"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    db.delete(host)
    db.commit()
    return {"message": "Host deleted successfully"}

@router.get("/{host_id}/history")
@require_auth  
async def get_host_history(
    host_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get host monitoring history"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    history = db.query(HostHistory).filter(
        HostHistory.hostname == host.hostname
    ).order_by(HostHistory.timestamp.desc()).limit(limit).all()
    
    return history

@router.post("/bulk-import")
@require_permission("edit_hosts")
async def bulk_import_hosts(hosts: List[HostCreate], db: Session = Depends(get_db)):
    """Bulk import hosts"""
    created_hosts = []
    errors = []
    
    for host_data in hosts:
        try:
            existing = db.query(Host).filter(Host.hostname == host_data.hostname).first()
            if existing:
                errors.append(f"Hostname {host_data.hostname} already exists")
                continue
            
            db_host = Host(**host_data.dict())
            db.add(db_host)
            created_hosts.append(db_host)
            
        except Exception as e:
            errors.append(f"Error creating {host_data.hostname}: {str(e)}")
    
    db.commit()
    
    return {
        "created": len(created_hosts),
        "errors": errors,
        "hosts": created_hosts
    }
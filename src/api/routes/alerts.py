"""Alert management API routes"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...models.base import SessionLocal
from ...models.alert import AlertRule, AlertInstance, NotificationChannel, AlertSeverity, AlertStatus, NotificationType
from ...services.alerts import AlertService
from ...auth.middleware import require_auth, require_permission

router = APIRouter()
alert_service = AlertService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    condition_type: str = "status"
    condition_operator: str = "equals"
    condition_value: str = "Offline"
    threshold_duration: int = 300
    target_hosts: Optional[str] = None
    target_tags: Optional[str] = None
    target_groups: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.MEDIUM
    notification_channels: Optional[str] = None
    enabled: bool = True

class NotificationChannelCreate(BaseModel):
    name: str
    type: NotificationType
    config: Dict[str, Any]
    enabled: bool = True

@router.get("/rules", response_model=List[Dict])
@require_auth
async def get_alert_rules(db: Session = Depends(get_db)):
    """Get all alert rules"""
    rules = db.query(AlertRule).all()
    return [
        {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "condition_type": rule.condition_type,
            "condition_operator": rule.condition_operator,
            "condition_value": rule.condition_value,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "created_at": rule.created_at
        }
        for rule in rules
    ]

@router.post("/rules")
@require_permission("manage_alerts")
async def create_alert_rule(rule: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create new alert rule"""
    db_rule = AlertRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/active", response_model=List[Dict])
@require_auth
async def get_active_alerts(limit: int = 100, db: Session = Depends(get_db)):
    """Get active alerts"""
    alerts = db.query(AlertInstance).filter(
        AlertInstance.status == AlertStatus.ACTIVE
    ).order_by(AlertInstance.triggered_at.desc()).limit(limit).all()
    
    return [
        {
            "id": alert.id,
            "hostname": alert.hostname,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "triggered_at": alert.triggered_at,
            "notification_count": alert.notification_count
        }
        for alert in alerts
    ]

@router.post("/{alert_id}/acknowledge")
@require_permission("manage_alerts")
async def acknowledge_alert(alert_id: int, acknowledged_by: str, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    success = alert_service.acknowledge_alert(alert_id, acknowledged_by)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or cannot be acknowledged")
    
    return {"message": "Alert acknowledged successfully"}

@router.get("/channels", response_model=List[Dict])
@require_auth
async def get_notification_channels(db: Session = Depends(get_db)):
    """Get all notification channels"""
    channels = db.query(NotificationChannel).all()
    return [
        {
            "id": channel.id,
            "name": channel.name,
            "type": channel.type.value,
            "enabled": channel.enabled,
            "success_count": channel.success_count,
            "error_count": channel.error_count,
            "last_used": channel.last_used
        }
        for channel in channels
    ]

@router.post("/channels")
@require_permission("manage_alerts")
async def create_notification_channel(channel: NotificationChannelCreate, db: Session = Depends(get_db)):
    """Create notification channel"""
    db_channel = alert_service.create_notification_channel(
        name=channel.name,
        channel_type=channel.type,
        config=channel.config
    )
    return db_channel

@router.post("/test-notification/{channel_id}")
@require_permission("manage_alerts")
async def test_notification_channel(channel_id: int, db: Session = Depends(get_db)):
    """Test notification channel"""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Create test alert instance
    from datetime import datetime, timezone
    test_alert = AlertInstance(
        rule_id=0,
        hostname="test-host",
        title="Test Notification",
        message="This is a test notification from Sistemas Olivium Network Monitor",
        severity=AlertSeverity.LOW,
        triggered_at=datetime.now(timezone.utc)
    )
    
    success = alert_service._send_notification(channel, test_alert, is_resolution=False)
    return {"success": success, "message": "Test notification sent" if success else "Failed to send test notification"}
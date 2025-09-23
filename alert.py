"""Alert and notification models"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Enum, JSON
from .base import BaseModel
import enum

class AlertSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"

class NotificationType(enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"

class AlertRule(BaseModel):
    """Alert rule configuration"""
    __tablename__ = "alert_rules"
    
    # Identity
    name = Column(String(100), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    
    # Conditions
    condition_type = Column(String(20), default="status")  # status, latency, availability
    condition_operator = Column(String(10), default="equals")  # equals, greater_than, less_than
    condition_value = Column(String(50), default="Offline")
    
    # Thresholds
    threshold_duration = Column(Integer, default=300)  # seconds
    threshold_count = Column(Integer, default=1)
    
    # Targeting
    target_hosts = Column(Text)  # JSON array of hostnames or "*"
    target_tags = Column(Text)   # JSON array of tags
    target_groups = Column(Text) # JSON array of groups
    
    # Notification
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM)
    notification_channels = Column(Text)  # JSON array of channel IDs
    
    # Control
    suppression_duration = Column(Integer, default=300)  # seconds
    max_alerts_per_hour = Column(Integer, default=10)

class AlertInstance(BaseModel):
    """Active alert instances"""
    __tablename__ = "alert_instances"
    
    # References
    rule_id = Column(Integer, nullable=False)
    hostname = Column(String(255), nullable=False, index=True)
    
    # Status
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    severity = Column(Enum(AlertSeverity), nullable=False)
    
    # Details
    title = Column(String(200), nullable=False)
    message = Column(Text)
    
    # Timing
    triggered_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Metadata
    trigger_value = Column(String(100))
    acknowledged_by = Column(String(50))
    
    # Notification tracking
    notification_count = Column(Integer, default=0)
    last_notification = Column(DateTime)

class NotificationChannel(BaseModel):
    """Notification channel configuration"""
    __tablename__ = "notification_channels"
    
    # Identity
    name = Column(String(100), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    enabled = Column(Boolean, default=True)
    
    # Configuration
    config = Column(JSON)  # Channel-specific configuration
    
    # Examples:
    # Email: {"smtp_server": "...", "recipients": [...]}
    # Slack: {"webhook_url": "...", "channel": "#alerts"}
    # Webhook: {"url": "...", "method": "POST", "headers": {...}}
    
    # Status
    last_used = Column(DateTime)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
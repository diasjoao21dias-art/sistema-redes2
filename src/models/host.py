"""Host and monitoring related models"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
from .base import BaseModel
import enum

class HostStatus(enum.Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    WARNING = "Warning"
    UNKNOWN = "Unknown"
    MAINTENANCE = "Maintenance"

class CheckType(enum.Enum):
    ICMP = "icmp"
    TCP = "tcp"
    HTTP = "http"
    HTTPS = "https"
    DNS = "dns"
    SNMP = "snmp"
    CUSTOM = "custom"

class Host(BaseModel):
    """Host configuration and metadata"""
    __tablename__ = "hosts"
    
    # Identity
    hostname = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255))
    
    # Network info
    ip_address = Column(String(45))  # Support IPv6
    fallback_ip = Column(String(45))  # From CSV import
    mac_address = Column(String(17))
    
    # Configuration
    check_interval = Column(Integer, default=60)  # seconds
    timeout = Column(Integer, default=5)  # seconds
    check_types = Column(String(500), default="icmp,tcp")  # comma-separated
    tcp_ports = Column(String(500), default="3389,445,80,443,22")
    
    # Organization
    tags = Column(Text)  # JSON array of tags
    group_name = Column(String(100))
    site = Column(String(100))
    
    # Status
    enabled = Column(Boolean, default=True)
    in_maintenance = Column(Boolean, default=False)
    maintenance_until = Column(DateTime)
    
    # Metadata
    description = Column(Text)
    os_type = Column(String(50))
    device_type = Column(String(50), default="computer")

class HostHistory(BaseModel):
    """Historical monitoring data"""
    __tablename__ = "host_history"
    
    # References
    hostname = Column(String(255), index=True, nullable=False)
    
    # Status info
    status = Column(Enum(HostStatus), nullable=False)
    check_type = Column(Enum(CheckType))
    
    # Network info  
    ip = Column(String(45))
    latency_ms = Column(Float)
    
    # Timing
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    # Details
    reason = Column(String(200))
    error_message = Column(Text)
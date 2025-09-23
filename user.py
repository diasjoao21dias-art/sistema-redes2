"""User management and authentication models"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .base import BaseModel
import hashlib
import secrets

class Role(BaseModel):
    """User roles for RBAC"""
    __tablename__ = "roles"
    
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    # Permissions
    can_view = Column(Boolean, default=True)
    can_edit_hosts = Column(Boolean, default=False)
    can_manage_alerts = Column(Boolean, default=False)
    can_admin = Column(Boolean, default=False)

class User(BaseModel):
    """User accounts"""
    __tablename__ = "users"
    
    # Identity
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100))
    
    # Authentication
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # API access
    api_key = Column(String(64), unique=True, index=True)
    api_key_active = Column(Boolean, default=False)
    
    # Sessions
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    
    def set_password(self, password: str):
        """Hash and set password"""
        salt = secrets.token_hex(16)
        self.password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex() + ':' + salt
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        if not self.password_hash:
            return False
        try:
            hash_part, salt = self.password_hash.split(':')
            return hash_part == hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()
        except:
            return False
    
    def generate_api_key(self):
        """Generate new API key"""
        self.api_key = secrets.token_urlsafe(48)
        self.api_key_active = True
        return self.api_key

class UserRole(BaseModel):
    """User role assignments"""
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    # Relationships
    user = relationship("User", backref="role_assignments")
    role = relationship("Role", backref="user_assignments")
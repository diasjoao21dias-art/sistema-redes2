"""Authentication service with JWT and session management"""

from jose import JWTError, jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from ..models.user import User, Role, UserRole
from ..models.base import SessionLocal

class AuthService:
    """Professional authentication service"""
    
    def __init__(self, secret_key: str = None):
        import os
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY') or 'olivium-default-secret-key-change-in-production'
        self.algorithm = "HS256"
        self.token_expire_hours = 24
    
    def create_access_token(self, username: str, user_id: int, roles: list = None) -> str:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(hours=self.token_expire_hours)
        
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "roles": roles or [],
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Tuple[Optional[dict], bool]:
        """Authenticate user credentials"""
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username).first()
            
            if not user or not user.is_active:
                return None, False
                
            if user.verify_password(password):
                # Update login stats
                user.last_login = datetime.now(timezone.utc)
                user.login_count = (user.login_count or 0) + 1
                db.commit()
                
                # Return dict to avoid session issues
                user_dict = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active
                }
                return user_dict, True
                
            return None, False
    
    def authenticate_api_key(self, api_key: str) -> Optional[dict]:
        """Authenticate via API key"""
        with SessionLocal() as db:
            user = db.query(User).filter(
                User.api_key == api_key, 
                User.api_key_active == True,
                User.is_active == True
            ).first()
            if user:
                return {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active
                }
            return None
    
    def get_user_roles(self, user_id: int) -> list:
        """Get user roles"""
        with SessionLocal() as db:
            roles = db.query(Role).join(UserRole).filter(
                UserRole.user_id == user_id
            ).all()
            return [role.name for role in roles]
    
    def create_user(self, username: str, email: str, password: str, 
                   full_name: str = None, role_name: str = "viewer") -> User:
        """Create new user account"""
        with SessionLocal() as db:
            # Check if user exists
            if db.query(User).filter(User.username == username).first():
                raise ValueError("Username already exists")
            if db.query(User).filter(User.email == email).first():
                raise ValueError("Email already exists")
            
            # Create user
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                is_active=True
            )
            user.set_password(password)
            db.add(user)
            db.flush()  # Get user ID
            
            # Assign default role
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                db.add(user_role)
            
            db.commit()
            return user
    
    def setup_default_roles(self):
        """Setup default system roles"""
        default_roles = [
            {
                "name": "admin",
                "description": "Full system access",
                "can_view": True,
                "can_edit_hosts": True,
                "can_manage_alerts": True,
                "can_admin": True
            },
            {
                "name": "operator", 
                "description": "Manage hosts and alerts",
                "can_view": True,
                "can_edit_hosts": True,
                "can_manage_alerts": True,
                "can_admin": False
            },
            {
                "name": "viewer",
                "description": "View only access",
                "can_view": True,
                "can_edit_hosts": False,
                "can_manage_alerts": False,
                "can_admin": False
            }
        ]
        
        with SessionLocal() as db:
            for role_data in default_roles:
                existing = db.query(Role).filter(Role.name == role_data["name"]).first()
                if not existing:
                    role = Role(**role_data)
                    db.add(role)
            db.commit()
    
    def setup_default_admin(self, username: str = "admin", 
                           password: str = "admin123", 
                           email: str = "admin@sistemas-olivium.com") -> dict:
        """Setup default admin user"""
        self.setup_default_roles()
        
        with SessionLocal() as db:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                # Return dict to avoid session issues
                return {
                    'id': existing.id,
                    'username': existing.username,
                    'email': existing.email,
                    'api_key': existing.api_key or 'no-api-key-generated'
                }
            
            # Create new admin user
            admin = User(
                username=username,
                email=email,
                full_name="Administrator",
                password_hash=self._hash_password(password),
                is_active=True,
                is_superuser=True,
                api_key=secrets.token_urlsafe(32),
                api_key_active=True  # Enable API key authentication
            )
            db.add(admin)
            db.flush()  # Get ID
            
            # Add admin role
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if admin_role:
                user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
                db.add(user_role)
            
            db.commit()
            
            # Return dict to avoid session issues
            return {
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'api_key': admin.api_key
            }
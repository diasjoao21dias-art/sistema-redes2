"""FastAPI authentication dependencies"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from .service import AuthService
from ..models.base import SessionLocal

# Security scheme
security = HTTPBearer()
auth_service = AuthService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return {
        'id': payload['user_id'],
        'username': payload['sub'],
        'roles': payload.get('roles', [])
    }

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    payload = auth_service.verify_token(credentials.credentials)
    if not payload:
        return None
    
    return {
        'id': payload['user_id'], 
        'username': payload['sub'],
        'roles': payload.get('roles', [])
    }

def require_role(required_role: str):
    """Dependency factory for role-based access control"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = current_user.get('roles', [])
        
        # Admin has all permissions
        if 'admin' in user_roles:
            return current_user
        
        # Check specific role
        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return current_user
    
    return role_checker

def require_permission(permission: str):
    """Dependency factory for permission-based access control"""
    def permission_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = current_user.get('roles', [])
        
        # Admin has all permissions
        if 'admin' in user_roles:
            return current_user
        
        # Permission to role mapping
        permission_role_map = {
            'view': ['viewer', 'operator', 'admin'],
            'edit_hosts': ['operator', 'admin'], 
            'manage_alerts': ['operator', 'admin'],
            'admin': ['admin']
        }
        
        allowed_roles = permission_role_map.get(permission, [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return current_user
    
    return permission_checker

def require_api_key(api_key: str = None) -> dict:
    """Authenticate via API key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    user = auth_service.authenticate_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # user is now a dict, not an object
    roles = auth_service.get_user_roles(user['id'])
    return {
        'id': user['id'],
        'username': user['username'],
        'roles': roles
    }
"""User management API routes"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...models.base import SessionLocal
from ...models.user import User, Role
from ...auth.service import AuthService
from ...auth.middleware import require_auth, require_permission, get_current_user

router = APIRouter()
auth_service = AuthService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/me")
@require_auth
async def get_current_user_info(db: Session = Depends(get_db)):
    """Get current user information"""
    current_user = get_current_user()
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == current_user['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": current_user.get('roles', []),
        "last_login": user.last_login,
        "login_count": user.login_count
    }

@router.get("/", response_model=List[dict])
@require_permission("admin")
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    result = []
    
    for user in users:
        roles = auth_service.get_user_roles(user.id)
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "roles": roles,
            "last_login": user.last_login,
            "login_count": user.login_count,
            "created_at": user.created_at
        })
    
    return result

@router.put("/me")
@require_auth
async def update_current_user(user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update current user profile"""
    current_user = get_current_user()
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == current_user['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return {"message": "Profile updated successfully"}

@router.post("/me/api-key")
@require_auth
async def generate_api_key(db: Session = Depends(get_db)):
    """Generate new API key for current user"""
    current_user = get_current_user()
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == current_user['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    api_key = user.generate_api_key()
    db.commit()
    
    return {
        "api_key": api_key,
        "message": "New API key generated successfully"
    }

@router.delete("/me/api-key")
@require_auth
async def revoke_api_key(db: Session = Depends(get_db)):
    """Revoke current user's API key"""
    current_user = get_current_user()
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == current_user['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.api_key_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}

@router.get("/roles")
@require_auth
async def get_roles(db: Session = Depends(get_db)):
    """Get all available roles"""
    roles = db.query(Role).all()
    return [
        {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": {
                "can_view": role.can_view,
                "can_edit_hosts": role.can_edit_hosts,
                "can_manage_alerts": role.can_manage_alerts,
                "can_admin": role.can_admin
            }
        }
        for role in roles
    ]
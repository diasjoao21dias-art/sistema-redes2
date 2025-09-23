"""Authentication API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from ...auth.service import AuthService
from ...auth.models import UserLogin, UserCreate, TokenResponse, UserResponse
from ...models.base import SessionLocal

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user, success = auth_service.authenticate_user(credentials.username, credentials.password)
    
    if not success or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    roles = auth_service.get_user_roles(user["id"])
    token = auth_service.create_access_token(user["username"], user["id"], roles)
    
    user_response = UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        is_active=user["is_active"],
        roles=roles
    )
    
    return TokenResponse(
        access_token=token,
        expires_in=24*3600,
        user=user_response
    )

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user account"""
    try:
        user = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role_name=user_data.role
        )
        
        roles = auth_service.get_user_roles(user.id)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=roles
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/setup-admin")
async def setup_admin():
    """Setup default admin user (development only)"""
    import os
    if os.getenv('ENVIRONMENT') == 'production':
        raise HTTPException(status_code=403, detail="Not available in production")
    
    admin = auth_service.setup_default_admin()
    return {
        "message": "Admin user created", 
        "username": admin["username"],
        "api_key": admin["api_key"]
    }
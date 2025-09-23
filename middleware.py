"""Authentication middleware for Flask"""

from functools import wraps
from flask import request, jsonify, g
from typing import Optional
from .service import AuthService

# Global auth service instance
auth_service = AuthService()

def get_current_user() -> Optional[dict]:
    """Get current authenticated user from request context"""
    return getattr(g, 'current_user', None)

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        api_key = None
        
        # Check for JWT token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Check for API key in header or query param
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        user = None
        
        # Try JWT token first
        if token:
            payload = auth_service.verify_token(token)
            if payload:
                user = {
                    'id': payload['user_id'],
                    'username': payload['sub'],
                    'roles': payload.get('roles', [])
                }
        
        # Try API key if no valid token
        elif api_key:
            user_obj = auth_service.authenticate_api_key(api_key)
            if user_obj:
                roles = auth_service.get_user_roles(user_obj.id)
                user = {
                    'id': user_obj.id,
                    'username': user_obj.username,
                    'roles': roles
                }
        
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(required_role: str):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_roles = user.get('roles', [])
            
            # Admin has all permissions
            if 'admin' in user_roles:
                return f(*args, **kwargs)
            
            # Check specific role
            if required_role not in user_roles:
                return jsonify({'error': f'Role {required_role} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            # For now, map permissions to roles
            permission_role_map = {
                'view': 'viewer',
                'edit_hosts': 'operator', 
                'manage_alerts': 'operator',
                'admin': 'admin'
            }
            
            required_role = permission_role_map.get(permission)
            if not required_role:
                return jsonify({'error': 'Invalid permission'}), 400
            
            user_roles = user.get('roles', [])
            
            # Admin has all permissions
            if 'admin' in user_roles:
                return f(*args, **kwargs)
            
            # Check if user has required role or higher
            role_hierarchy = ['viewer', 'operator', 'admin']
            user_level = max([role_hierarchy.index(role) for role in user_roles if role in role_hierarchy] + [-1])
            required_level = role_hierarchy.index(required_role)
            
            if user_level < required_level:
                return jsonify({'error': f'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
from typing import List, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.database import db
from app.core.security import decode_access_token
from app.schemas.api import UserResponse

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_test_user_id: Optional[str] = Header(None)
) -> UserResponse:
    # 1. Allow X-Test-User-Id header for programmatic testing
    if x_test_user_id:
        try:
            uid = UUID(x_test_user_id)
            if uid in db.users:
                u = db.users[uid]
                return UserResponse(
                    id=u["id"],
                    tenant_id=u["tenant_id"],
                    email=u["email"],
                    role=u["role"],
                    status=u["status"],
                    created_at=u["created_at"]
                )
        except Exception:
            pass

    # 2. Inspect Bearer token
    if not credentials:
        # Default to customer user if no auth is passed for public intake testing
        default_user = list(db.users.values())[0]
        return UserResponse(
            id=default_user["id"],
            tenant_id=default_user["tenant_id"],
            email=default_user["email"],
            role=default_user["role"],
            status=default_user["status"],
            created_at=default_user["created_at"]
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials."
        )

    user_id = UUID(payload["sub"])
    if user_id not in db.users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists."
        )

    user = db.users[user_id]
    return UserResponse(
        id=user["id"],
        tenant_id=user["tenant_id"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"]
    )

def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to access this resource."
            )
        return current_user
    return role_checker

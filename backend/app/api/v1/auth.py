from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import db
from app.core.security import create_access_token
from app.core.auth import get_current_user
from app.schemas.api import TokenResponse, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    for uid, user in db.users.items():
        if user["email"] == credentials.email:
            if user["password"] == credentials.password:
                token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
                user_res = UserResponse(
                    id=user["id"],
                    tenant_id=user["tenant_id"],
                    email=user["email"],
                    role=user["role"],
                    status=user["status"],
                    created_at=user["created_at"]
                )
                return TokenResponse(access_token=token, token_type="bearer", user=user_res)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password."
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with email '{credentials.email}' was not found."
    )

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

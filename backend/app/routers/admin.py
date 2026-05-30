from fastapi import APIRouter, HTTPException, status

from app.schemas.admin import AdminLoginRequest, AdminLoginResponse
from app.security import create_admin_token, verify_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest) -> AdminLoginResponse:
    if not verify_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    return AdminLoginResponse(token=create_admin_token())

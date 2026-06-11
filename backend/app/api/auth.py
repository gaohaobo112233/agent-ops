from fastapi import APIRouter, HTTPException
from app.api.schemas import LoginRequest, LoginResponse
from app.core.security import authenticate

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    token = authenticate(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return LoginResponse(token=token)

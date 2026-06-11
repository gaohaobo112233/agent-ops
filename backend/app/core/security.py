from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import settings

security_scheme = HTTPBearer()


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="认证令牌已过期或无效")


def authenticate(username: str, password: str) -> str | None:
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        return create_access_token({"sub": username})
    return None

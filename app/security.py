from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(value: str) -> str:
    return password_hasher.hash(value)

def verify_password(value: str, hashed: str) -> bool:
    return password_hasher.verify(value, hashed)

def make_token(user: User) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": expiry}, settings.SECRET_KEY, algorithm="HS256")

def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    error = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise error
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise error

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active.is_(True)
    ).first()

    if not user:
        raise error

    return user

def allow_roles(*roles):
    def guard(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission to perform this action")
        return user
    return guard

patient_only = allow_roles("patient")
doctor_only = allow_roles("doctor")
admin_only = allow_roles("admin")
doctor_or_admin = allow_roles("doctor", "admin")

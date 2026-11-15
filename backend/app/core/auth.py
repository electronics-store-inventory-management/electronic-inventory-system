from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db, settings
from app.models.user import User

ALGORITHM = "HS256"


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    if not settings.JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication")

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    if user.role not in {"admin", "employee"}:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: admin required",
        )
    return current_user
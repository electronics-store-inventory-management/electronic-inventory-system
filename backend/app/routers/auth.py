from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.password_security import hash_password, verify_password
from app.database.database import get_db, settings
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

@router.post("/register", status_code=201)
def register(credentials: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(User.username == credentials.username)
        .first()
    )

    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=credentials.username,
        hashed_password=hash_password(credentials.password),
        role="employee",
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not create user")

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }


@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.username == credentials.username)
        .first()
    )

    if user is None or not verify_password(
        credentials.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    secret = settings.JWT_SECRET_KEY
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured",
        )

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        },
        secret,
        algorithm=ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }

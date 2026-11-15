from unicodedata import category
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import ALGORITHM, get_current_user
from app.core.password_security import hash_password, verify_password
from app.database.database import get_db, settings
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
DUMMY_PASSWORD_HASH = hash_password(token_urlsafe(32))


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, password: str) -> str:
        if not any(char.isalpha() for char in password) or not any(category(char)[0] in "NPS" for char in password):
            raise ValueError("Use a letter and at least one number or symbol.")
        return password


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AccountResponse(BaseModel):
    id: int
    username: str
    role: str


def limit_registration(request: Request):
    if not settings.REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="Public signup is currently unavailable.")
    request.app.state.auth_limiter.check(request, "register", settings.REGISTRATION_REQUESTS_PER_MINUTE)


def limit_login(request: Request):
    request.app.state.auth_limiter.check(request, "login", settings.LOGIN_REQUESTS_PER_MINUTE)


@router.post("/register", status_code=201, response_model=AccountResponse, dependencies=[Depends(limit_registration)])
def register(credentials: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User.id).filter(User.username == credentials.username).first() is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=credentials.username,
        hashed_password=hash_password(credentials.password),
        role="employee",
    )
    try:
        db.add(user)
        db.flush()
        account = AccountResponse(id=user.id, username=user.username, role=user.role)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "pgcode", None) == "23505":
            raise HTTPException(status_code=409, detail="Username already exists") from None
        raise

    return account


@router.post("/login", dependencies=[Depends(limit_login)])
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    valid = verify_password(credentials.password, user.hashed_password if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    secret = settings.JWT_SECRET_KEY
    if not secret:
        raise HTTPException(status_code=503, detail="Authentication is unavailable")

    now = datetime.now(timezone.utc)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(seconds=expires_in)},
        secret,
        algorithm=ALGORITHM,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


@router.get("/me", response_model=AccountResponse)
def me(response: Response, user: dict = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user

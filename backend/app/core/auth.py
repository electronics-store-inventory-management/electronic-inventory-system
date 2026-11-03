from typing import Optional

from fastapi import Depends, Header, HTTPException

USERS = {
    "admin": {"id": 1, "username": "admin", "role": "admin"},
    "employee": {"id": 2, "username": "employee", "role": "employee"},
}

ADMIN_HEADERS = {"Authorization": "Bearer admin-token"}
EMPLOYEE_HEADERS = {"Authorization": "Bearer employee-token"}

TOKEN_TO_USER = {
    "admin-token": USERS["admin"],
    "employee-token": USERS["employee"],
}


def get_current_user(authorization: Optional[str] = Header(default=None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token not in TOKEN_TO_USER:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return TOKEN_TO_USER[token]


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: admin required")
    return current_user

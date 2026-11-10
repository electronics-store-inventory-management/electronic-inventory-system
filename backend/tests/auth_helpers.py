from datetime import datetime, timedelta, timezone

import jwt

from app.database.database import settings

# Test-only secret. Never use this secret in production.
settings.JWT_SECRET_KEY = "test-only-secret-key-not-for-production"

ALGORITHM = "HS256"


def make_test_headers(user_id: int, username: str, role: str) -> dict:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


ADMIN_HEADERS = make_test_headers(1, "admin", "admin")
EMPLOYEE_HEADERS = make_test_headers(2, "employee", "employee")

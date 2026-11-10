from app.models.user import User


def seed_test_users(db):
    users = [
        {"id": 1, "username": "admin", "role": "admin"},
        {"id": 2, "username": "employee", "role": "employee"},
    ]

    for data in users:
        existing = db.query(User).filter(User.id == data["id"]).first()

        if existing is None:
            db.add(
                User(
                    id=data["id"],
                    username=data["username"],
                    role=data["role"],
                    hashed_password="test-only-not-a-real-password-hash",
                )
            )

    db.commit()

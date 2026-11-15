import argparse
import warnings
from getpass import GetPassWarning, getpass

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.password_security import hash_password
from app.database.database import DATABASE_URL, SessionLocal, engine
from app.models.product import Product
from app.models.user import User
from app.routers.auth import RegisterRequest
from app.schemas.product import ProductCreate
from app.schemas.transaction import InventoryTransactionCreate
from app.services.product_service import create_product
from app.services.transaction_service import record_transaction


def create_admin(username: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Admin password: ")
            confirmation = getpass("Confirm password: ")
    except GetPassWarning:
        raise SystemExit("Use an interactive terminal that can hide the password.") from None
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        account = RegisterRequest(username=username, password=password)
    except ValidationError:
        raise SystemExit("Use a valid 3–50 character username and a 12–128 character password with a letter and a number or symbol.") from None
    try:
        with SessionLocal.begin() as db:
            if db.scalar(select(User.id).where(User.username == username)) is not None:
                raise SystemExit("That username already exists. No account was updated.")
            db.add(User(username=account.username, hashed_password=hash_password(account.password), role="admin"))
    except IntegrityError:
        raise SystemExit("Administrator creation conflicted with an existing record. No account was updated.") from None
    print(f"Created administrator {username}.")


def seed_demo(admin_name: str) -> None:
    samples = [
        ("[Demo] USB-C Dock", "2899.50", 6, 10),
        ("[Demo] Travel Charger", "1299.00", 24, 8),
        ("[Demo] Display Adapter", "749.00", 0, 5),
    ]
    key = 230023  # Dedicated lock for the demo-data command.
    messages = []
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        # The service methods commit savepoints; the complete seed commits together.
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            admin = db.scalar(select(User).where(User.username == admin_name, User.role == "admin"))
            if admin is None:
                raise SystemExit("An existing administrator is required to attribute demo records.")
            user_id = admin.id
            for name, price, quantity, minimum in samples:
                if db.scalar(select(Product.id).where(Product.name == name).limit(1)) is not None:
                    messages.append(f"Skipped existing {name}.")
                    continue
                product = create_product(db, ProductCreate(
                    name=name, category="ElectroStock Demo", price=price, quantity=0,
                    min_stock_level=minimum,
                ), user_id=user_id)
                record_transaction(db, InventoryTransactionCreate(
                    product_id=product.id, transaction_type="ADD" if quantity else "SET",
                    quantity=quantity, user_id=user_id, reference="ElectroStock demo seed",
                ), authenticated_user_id=user_id)
                messages.append(f"Created {name}.")
    for message in messages:
        print(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="ElectroStock database administration")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="Create a new administrator with a hidden password prompt")
    admin.add_argument("username")
    demo = commands.add_parser("seed-demo", help="Add clearly labelled sample inventory and transactions")
    demo.add_argument("--admin", required=True)
    args = parser.parse_args()
    print(f"Database target: {DATABASE_URL.host}:{DATABASE_URL.port or 5432}/{DATABASE_URL.database}")
    try:
        if args.command == "create-admin":
            create_admin(args.username)
        else:
            seed_demo(args.admin)
    except SQLAlchemyError:
        raise SystemExit("Database operation failed. Check the connection, migrations, and permissions.") from None


if __name__ == "__main__":
    main()

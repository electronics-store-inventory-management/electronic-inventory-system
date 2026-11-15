"""Create the existing account schema on databases missing the users table."""
import sqlalchemy as sa
from alembic import op

revision = "20261115_02"
down_revision = "20261108_01"
branch_labels = None
depends_on = None


def validate_existing_users(inspector):
    problems = []
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    if inspector.get_pk_constraint("users")["constrained_columns"] != ["id"]:
        problems.append("id must be the sole primary key")
    identifier = columns.get("id")
    dialect = inspector.bind.dialect.name
    if (
        not identifier or not isinstance(identifier["type"], sa.Integer)
        or (dialect == "sqlite" and str(identifier["type"]) != "INTEGER")
        or (
            dialect == "postgresql" and identifier.get("identity") is None
            and not (identifier.get("default") or "").startswith("nextval(")
        )
    ):
        problems.append("id must be an automatically generated integer")
    for name, length in {"username": 50, "hashed_password": 255, "role": 20}.items():
        column = columns.get(name)
        if (
            not column or column["nullable"] or not isinstance(column["type"], sa.String)
            or isinstance(column["type"], sa.CHAR)
            or (column["type"].length is not None and column["type"].length < length)
        ):
            problems.append(f"{name} must be non-null text with room for at least {length} characters")

    unique_username = any(
        constraint["column_names"] == ["username"]
        for constraint in inspector.get_unique_constraints("users")
    ) or any(
        index["unique"] and index["column_names"] == ["username"]
        and not any(key.endswith("_where") for key in index.get("dialect_options", {}))
        and not index.get("dialect_options", {}).get("postgresql_invalid")
        for index in inspector.get_indexes("users")
    )
    if not unique_username:
        problems.append("username requires a non-partial unique constraint or index")
    for name, column in columns.items():
        if (
            name not in {"id", "username", "hashed_password", "role"} and not column["nullable"]
            and column.get("default") is None and not (column.get("identity") or column.get("computed"))
        ):
            problems.append(f"extra column {name} requires a value the app cannot supply")
    if problems:
        raise RuntimeError(
            "Incompatible users table: " + "; ".join(problems)
            + ". Back up the database, review the existing schema and records, and have a database operator "
            "repair the schema before rerunning this migration. This revision did not modify any user records."
        )


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("users"):
        validate_existing_users(inspector)
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="employee"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade():
    # The table can predate this revision and can hold real accounts.
    pass

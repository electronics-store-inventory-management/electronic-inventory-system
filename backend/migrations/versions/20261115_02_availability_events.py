"""Track observed service availability transitions."""
from alembic import op
import sqlalchemy as sa

revision = "20261115_02"
down_revision = "20261115_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "availability_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_availability_events_checked_at", "availability_events", ["checked_at"])


def downgrade():
    op.drop_index("ix_availability_events_checked_at", table_name="availability_events")
    op.drop_table("availability_events")

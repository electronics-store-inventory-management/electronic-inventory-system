"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${":" if upgrades else "pass"}
    ${upgrades | indent(4, true)}


def downgrade():
    ${":" if downgrades else "pass"}
    ${downgrades | indent(4, true)}

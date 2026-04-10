"""Add pin_hash column to users table"""

import sqlalchemy as sa
from alembic import op

revision = "add_pin_hash"
down_revision = "postgre_core_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.add_column("users", sa.Column("pin_hash", sa.Text(), nullable=True))


def downgrade() -> None:
	op.drop_column("users", "pin_hash")

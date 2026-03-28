"""Add frozen_by, frozen_at, freeze_reason columns to bank_accounts"""

from alembic import op
import sqlalchemy as sa

revision = "add_freeze_columns"
down_revision = "add_transactions_account_id_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bank_accounts",
        sa.Column("frozen_by", sa.Text(), nullable=True),
    )
    op.add_column(
        "bank_accounts",
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bank_accounts",
        sa.Column("freeze_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bank_accounts", "freeze_reason")
    op.drop_column("bank_accounts", "frozen_at")
    op.drop_column("bank_accounts", "frozen_by")

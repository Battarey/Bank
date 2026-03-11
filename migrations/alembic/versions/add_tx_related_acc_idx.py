"""Add index on transactions.related_account_id"""

from alembic import op

revision = "add_tx_related_acc_idx"
down_revision = "add_transactions_acc_created_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_related_account_id",
        "transactions",
        ["related_account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_related_account_id", table_name="transactions")

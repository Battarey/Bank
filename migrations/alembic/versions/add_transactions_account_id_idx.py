"""Add index on transactions.account_id for faster history lookups"""

from alembic import op

revision = "add_transactions_account_id_idx"
down_revision = "add_bank_accounts_client_id_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_account_id",
        "transactions",
        ["account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_account_id", table_name="transactions")

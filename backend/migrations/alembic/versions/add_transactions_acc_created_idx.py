"""Add index on transactions (account_id, created_at DESC)"""

import sqlalchemy as sa
from alembic import op

revision = "add_transactions_acc_created_idx"
down_revision = "add_currency_and_metal"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_index(
		"ix_transactions_acc_created",
		"transactions",
		["account_id", sa.text("created_at DESC")],
	)


def downgrade() -> None:
	op.drop_index("ix_transactions_acc_created", table_name="transactions")

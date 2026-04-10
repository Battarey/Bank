"""Add index on bank_accounts.client_id for faster lookups"""

from alembic import op

revision = "add_bank_accounts_client_id_idx"
down_revision = "add_pin_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_index(
		"ix_bank_accounts_client_id",
		"bank_accounts",
		["client_id"],
	)


def downgrade() -> None:
	op.drop_index("ix_bank_accounts_client_id", table_name="bank_accounts")

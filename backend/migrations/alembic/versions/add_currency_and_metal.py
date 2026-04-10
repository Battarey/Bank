"""Add exchange transaction type"""

from alembic import op

revision = "add_currency_and_metal"
down_revision = "add_freeze_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.drop_constraint("transactions_type_check", "transactions", type_="check")
	op.create_check_constraint(
		"transactions_type_check",
		"transactions",
		"type IN ('deposit', 'withdrawal', 'transfer', 'exchange')",
	)


def downgrade() -> None:
	op.drop_constraint("transactions_type_check", "transactions", type_="check")
	op.create_check_constraint(
		"transactions_type_check",
		"transactions",
		"type IN ('deposit', 'withdrawal', 'transfer')",
	)

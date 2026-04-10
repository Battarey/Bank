"""Add index on passport (series, number)"""

from alembic import op

revision = "add_passport_series_number_idx"
down_revision = "add_tx_related_acc_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_unique_constraint(
		"uq_passport_series_number",
		"passport",
		["series", "number"],
	)


def downgrade() -> None:
	op.drop_constraint("uq_passport_series_number", "passport", type_="unique")

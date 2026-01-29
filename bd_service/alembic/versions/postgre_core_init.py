"""Initial schema for postgre_core tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "postgre_core_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.CheckConstraint("status IN ('active', 'blocked', 'deleted')", name="users_status_check"),
    )

    # personal_data
    op.create_table(
        "personal_data",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.CHAR(length=1), nullable=False),
        sa.CheckConstraint("gender IN ('M', 'F')", name="personal_data_gender_check"),
    )

    # passport
    op.create_table(
        "passport",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("series", sa.CHAR(length=4), nullable=False),
        sa.Column("number", sa.CHAR(length=6), nullable=False),
        sa.Column("division_code", sa.CHAR(length=7), nullable=False),
        sa.Column("issued_by", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column("registration_address", sa.Text(), nullable=False),
    )

    # identifiers
    op.create_table(
        "identifiers",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("inn", sa.CHAR(length=12), nullable=False, unique=True),
        sa.Column("snils", sa.CHAR(length=11), nullable=False, unique=True),
    )

    # contacts
    op.create_table(
        "contacts",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("phone", sa.String(length=20), nullable=False, unique=True),
    )

    # bank_accounts
    op.create_table(
        "bank_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("account_number", sa.CHAR(length=20), nullable=False, unique=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('checking', 'savings', 'credit', 'deposit')",
            name="bank_accounts_type_check",
        ),
        sa.CheckConstraint("currency IN ('RUB', 'USD', 'EUR')", name="bank_accounts_currency_check"),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'frozen')",
            name="bank_accounts_status_check",
        ),
    )

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "related_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("balance_before", sa.Numeric(18, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "type IN ('deposit', 'withdrawal', 'transfer')",
            name="transactions_type_check",
        ),
        sa.CheckConstraint(
            "direction IN ('incoming', 'outgoing')",
            name="transactions_direction_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'posted', 'failed')",
            name="transactions_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("bank_accounts")
    op.drop_table("contacts")
    op.drop_table("identifiers")
    op.drop_table("passport")
    op.drop_table("personal_data")
    op.drop_table("users")

"""create_clients_table

Revision ID: 0001
Revises:
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("request_type", sa.String(), nullable=False),
        sa.Column("patrimony_value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("pipefy_card_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clients_email"), "clients", ["email"], unique=True)
    op.create_index(op.f("ix_clients_id"), "clients", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clients_id"), table_name="clients")
    op.drop_index(op.f("ix_clients_email"), table_name="clients")
    op.drop_table("clients")

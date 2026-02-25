"""add user_llm_keys table for BYOK

Revision ID: 0005
Revises: 0004
Create Date: 2025-02-25 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_llm_keys table."""
    op.create_table(
        "user_llm_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("OPENAI", "ANTHROPIC", "GOOGLE", name="llmprovidertype"),
            nullable=False,
        ),
        sa.Column("encrypted_key", sa.LargeBinary(), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("nonce", sa.LargeBinary(length=12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_llm_keys_user_provider"),
    )
    op.create_index("ix_user_llm_keys_user_id", "user_llm_keys", ["user_id"])


def downgrade() -> None:
    """Drop user_llm_keys table."""
    op.drop_index("ix_user_llm_keys_user_id", table_name="user_llm_keys")
    op.drop_table("user_llm_keys")
    sa.Enum(name="llmprovidertype").drop(op.get_bind(), checkfirst=True)

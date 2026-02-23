"""add pipeline_executions table

Revision ID: 0004
Revises: 0003
Create Date: 2025-02-23 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pipeline_executions table."""
    op.create_table(
        "pipeline_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("design_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="pipelineexecutionstatus"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("agent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_executions_user_id", "pipeline_executions", ["user_id"])


def downgrade() -> None:
    """Drop pipeline_executions table."""
    op.drop_index("ix_pipeline_executions_user_id", table_name="pipeline_executions")
    op.drop_table("pipeline_executions")
    sa.Enum(name="pipelineexecutionstatus").drop(op.get_bind())

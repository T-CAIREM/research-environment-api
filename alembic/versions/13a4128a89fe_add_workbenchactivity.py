"""Add WorkbenchActivity

Revision ID: 13a4128a89fe
Revises: 3955e608c536
Create Date: 2023-07-19 11:06:13.067945

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "13a4128a89fe"
down_revision = "3955e608c536"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workbench_workbench_activities",
        sa.Column("invoker_username", sa.String(), nullable=False),
        sa.Column(
            "build_type",
            sa.Enum(
                "WORKSPACE_CREATION",
                "WORKSPACE_DELETION",
                "JUPYTER_CREATION",
                "RSTUDIO_CREATION",
                "JUPYTER_CREATION_RETRY",
                "JUPYTER_STOP",
                "JUPYTER_START",
                "JUPYTER_UPDATE",
                name="buildtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "build_status",
            sa.Enum(
                "IN_PROGRESS",
                "FAILURE",
                "SUCCESS",
                name="status",
            ),
            nullable=False,
        ),
        sa.Column("build_error_information", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("workbench_workbench_activities")

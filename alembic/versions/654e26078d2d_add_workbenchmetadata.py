"""Add WorkbenchMetadata

Revision ID: 654e26078d2d
Revises:
Create Date: 2023-07-10 10:10:41.114559

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "654e26078d2d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workbench_workbench_metadata",
        sa.Column("gcp_identifier", sa.String(), nullable=False),
        sa.Column("dataset_slug", sa.String(), nullable=False),
        sa.Column("dataset_version", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("workbench_workbench_metadata")

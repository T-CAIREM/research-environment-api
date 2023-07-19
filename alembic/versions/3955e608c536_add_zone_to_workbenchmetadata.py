"""Add zone to WorkbenchMetadata

Revision ID: 3955e608c536
Revises: 654e26078d2d
Create Date: 2023-07-18 14:30:41.983317

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3955e608c536"
down_revision = "654e26078d2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workbench_workbench_metadata", sa.Column("zone", sa.String(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("workbench_workbench_metadata", "zone")

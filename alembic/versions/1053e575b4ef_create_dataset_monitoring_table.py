"""create dataset monitoring table

Revision ID: 1053e575b4ef
Revises: 7f6ecf630e82
Create Date: 2024-06-17 16:39:17.958860

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1053e575b4ef"
down_revision = "7f6ecf630e82"
branch_labels = None
depends_on = None

instance_type_enum = sa.Enum("JUPYTER", "RSTUDIO", name="instancetype")


def upgrade() -> None:
    op.create_table(
        "workbench_monitoring_data",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_identifier", sa.String(), nullable=False),
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime, server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime),
        sa.Column(
            "instance_type",
            instance_type_enum,
            nullable=False,
        ),
        sa.Column("workbench_id", sa.String(), nullable=False),
    )
    op.create_index(
        "idx_project_name", "workbench_monitoring_data", ["dataset_identifier"]
    )
    op.create_index("idx_user_email", "workbench_monitoring_data", ["user_email"])


def downgrade() -> None:
    op.drop_index("idx_project_name", table_name="workbench_monitoring_data")
    op.drop_index("idx_user_email", table_name="workbench_monitoring_data")
    op.drop_table("workbench_monitoring_data")
    instance_type_enum.drop(op.get_bind(), checkfirst=False)

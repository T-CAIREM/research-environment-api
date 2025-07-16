"""create workbench collaborators table

Revision ID: f70b6b5a89ae
Revises: 1053e575b4ef
Create Date: 2025-07-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f70b6b5a89ae"
down_revision = "1053e575b4ef"
branch_labels = None
depends_on = None

collaborator_status_enum = sa.Enum("SUCCESS", "FAILED", "REMOVED", name="collaboratorstatus")


def upgrade() -> None:
    op.create_table(
        "workbench_collaborators",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_project_id", sa.String(), nullable=False),
        sa.Column("service_account_name", sa.String(), nullable=False),
        sa.Column("collaborator_email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("viewed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", collaborator_status_enum, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_workbench_collaborators_service_account",
        "workbench_collaborators",
        ["service_account_name"],
    )
    op.create_index(
        "idx_workbench_collaborators_project_id",
        "workbench_collaborators",
        ["workspace_project_id"],
    )
    op.create_index(
        "idx_workbench_collaborators_email",
        "workbench_collaborators",
        ["collaborator_email"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_workbench_collaborators_service_account",
        table_name="workbench_collaborators",
    )
    op.drop_index(
        "idx_workbench_collaborators_project_id", table_name="workbench_collaborators"
    )
    op.drop_index(
        "idx_workbench_collaborators_email", table_name="workbench_collaborators"
    )
    op.drop_table("workbench_collaborators")
    collaborator_status_enum.drop(op.get_bind(), checkfirst=False)
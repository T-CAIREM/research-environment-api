"""add_sharing_statuses

Revision ID: b5d69f2e87da
Revises: 0335c8744390
Create Date: 2023-10-31 15:15:56.969740

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b5d69f2e87da"
down_revision = "0335c8744390"
branch_labels = None
depends_on = None


old_enum_options = (
    "WORKSPACE_CREATION",
    "WORKSPACE_DELETION",
    "WORKBENCH_CREATION",
    "WORKBENCH_STOP",
    "WORKBENCH_START",
    "WORKBENCH_UPDATE",
    "WORKBENCH_DESTROY",
)
new_enum_options = sorted(
    old_enum_options + ("SHARED_WORKSPACE_CREATION", "SHARED_WORKSPACE_DELETION")
)

old_type = sa.Enum(*old_enum_options, name="buildtype")
new_type = sa.Enum(*new_enum_options, name="buildtype")

tcr = sa.sql.table(
    "workbench_workbench_activities", sa.Column("build_type", new_type, nullable=False)
)


def upgrade():
    op.execute("ALTER TYPE buildtype RENAME TO temp_buildtype")

    new_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE workbench_workbench_activities ALTER COLUMN build_type TYPE buildtype USING build_type::text::buildtype"
    )
    op.execute("DROP TYPE temp_buildtype")


def downgrade():
    op.execute(
        tcr.update()
        .where(tcr.c.build_type == "SHARED_WORKSPACE_CREATION")
        .values(build_type="WORKSPACE_CREATION")
    )
    op.execute(
        tcr.update()
        .where(tcr.c.build_type == "SHARED_WORKSPACE_DELETION")
        .values(build_type="WORKSPACE_DELETION")
    )
    op.execute("ALTER TYPE buildtype RENAME TO temp_buildtype")
    old_type.create(op.get_bind())
    op.execute(
        "ALTER TABLE workbench_workbench_activities ALTER COLUMN build_type TYPE buildtype"
        " USING build_type::text::buildtype"
    )
    op.execute("DROP TYPE temp_buildtype")

"""add cascade to foreign keys

Revision ID: 918a61d2fe6
Revises: 844562c6ddf
Create Date: 2014-07-30 16:01:13.546643

"""

# revision identifiers, used by Alembic.
revision = '918a61d2fe6'
down_revision = '844562c6ddf'

from alembic import op


def upgrade():
    op.drop_constraint(
        "tasks_challenge_slug_fkey",
        "tasks")
    op.create_foreign_key(
        "tasks_challenge_slug_fkey",
        "tasks",
        "challenges",
        ["challenge_slug"],
        ["slug"],
        onupdate="cascade",
        ondelete="cascade")

    op.drop_constraint(
        "actions_task_id_fkey",
        "actions")
    op.create_foreign_key(
        "actions_task_id_fkey",
        "actions",
        "tasks",
        ["task_id"],
        ["id"],
        onupdate="cascade",
        ondelete="cascade")

    op.drop_constraint(
        "task_geometries_task_id_fkey",
        "task_geometries")
    op.create_foreign_key(
        "task_geometries_task_id_fkey",
        "task_geometries",
        "tasks",
        ["task_id"],
        ["id"],
        onupdate="cascade",
        ondelete="cascade")

    op.drop_constraint(
        "actions_user_id_fkey",
        "actions")
    op.create_foreign_key(
        "actions_user_id_fkey",
        "actions",
        "users",
        ["user_id"],
        ["id"],
        onupdate="cascade",
        ondelete="cascade")


def downgrade():
    op.drop_constraint(
        "tasks_challenge_slug_fkey",
        "tasks")
    op.create_foreign_key(
        "tasks_challenge_slug_fkey",
        "tasks",
        "challenges",
        ["challenge_slug"],
        ["slug"],
        onupdate="cascade")

    op.drop_constraint(
        "actions_task_id_fkey",
        "actions")
    op.create_foreign_key(
        "actions_task_id_fkey",
        "actions",
        "tasks",
        ["task_id"],
        ["id"],
        onupdate="cascade")

    op.drop_constraint(
        "task_geometries_task_id_fkey",
        "task_geometries")
    op.create_foreign_key(
        "task_geometries_task_id_fkey",
        "task_geometries",
        "tasks",
        ["task_id"],
        ["id"],
        onupdate="cascade")

    op.drop_constraint(
        "actions_user_id_fkey",
        "actions")
    op.create_foreign_key(
        "actions_user_id_fkey",
        "actions",
        "users",
        ["user_id"],
        ["id"],
        onupdate="cascade")

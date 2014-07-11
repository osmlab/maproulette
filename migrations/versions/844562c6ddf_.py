"""change primary key to challenge_slug + identifier in tasks table

Revision ID: 844562c6ddf
Revises: 1107fa473275
Create Date: 2014-07-10 16:29:47.975001

"""

# revision identifiers, used by Alembic.
revision = '844562c6ddf'
down_revision = '1107fa473275'

from alembic import op
import sqlalchemy as sa


def upgrade():
    #temporarily drop fkey constraint so we can drop the primary key
    op.drop_constraint(
        'actions_task_id_fkey',
        'actions')
    op.drop_constraint(
        'task_geometries_task_id_fkey',
        'task_geometries')
    # drop the old primary key
    op.drop_constraint(
        'tasks_pkey',
        'tasks')
    # change the challenge_slug column to be non nullable
    op.alter_column('tasks', 'challenge_slug',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
    # create the new one
    op.create_primary_key(
        'tasks_pkey',
        'tasks',
        ['identifier', 'challenge_slug'])
    # create an index on id column
    op.create_index(
        'idx_tasks_id',
        'tasks',
        ['id'])
    # recreate the foreign keys
    op.create_foreign_key(
        'actions_task_id_fkey',
        'actions',
        'tasks',
        ['task_id'],
        ['id'])
    op.create_foreign_key(
        'task_geometries_task_id_fkey',
        'task_geometries',
        'tasks',
        ['task_id'],
        ['id'])


def downgrade():
    #temporarily drop fkey constraints so we can drop the primary key
    op.drop_constraint(
        'actions_task_id_fkey',
        'actions')
    op.drop_constraint(
        'task_geometries_task_id_fkey',
        'task_geometries')
    op.drop_index('idx_tasks_id')
    op.drop_constraint(
        'tasks_pkey',
        'tasks')
    # change the challenge slug column to be nullable again
    op.alter_column('tasks', 'challenge_slug',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.create_primary_key(
        'tasks_pkey',
        'tasks',
        ['id'])
    # recreate the foreign keys
    op.create_foreign_key(
        'actions_task_id_fkey',
        'actions',
        'tasks',
        ['task_id'],
        ['id'])
    op.create_foreign_key(
        'task_geometries_task_id_fkey',
        'task_geometries',
        'tasks',
        ['task_id'],
        ['id'])

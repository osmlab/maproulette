"""changing field currentaction to status in tasks table

Revision ID: 38fe795129a0
Revises: None
Create Date: 2014-04-17 08:58:57.817750

"""

# revision identifiers, used by Alembic.
revision = '38fe795129a0'
down_revision = None

from alembic import op


def upgrade():
    op.alter_column('tasks', 'currentaction', new_column_name='status')


def downgrade():
    op.alter_column('tasks', 'status', new_column_name='currentaction')

"""adding user name columns

Revision ID: 1107fa473275
Revises: 585808afd671
Create Date: 2014-07-10 09:54:57.940819

"""

# revision identifiers, used by Alembic.
revision = '1107fa473275'
down_revision = '585808afd671'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('metrics_aggregate', sa.Column('user_name', sa.String(), nullable=True))
    op.create_index('idx_metrics_agg_username', 'metrics_aggregate', ['user_name'], unique=False)
    op.add_column('metrics_historical', sa.Column('user_name', sa.String(), nullable=True))
    op.create_index('idx_metrics_username', 'metrics_historical', ['user_name'], unique=False)


def downgrade():
    op.drop_index('idx_metrics_username', table_name='metrics_historical')
    op.drop_column('metrics_historical', 'user_name')
    op.drop_index('idx_metrics_agg_username', table_name='metrics_aggregate')
    op.drop_column('metrics_aggregate', 'user_name')
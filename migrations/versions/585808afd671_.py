"""empty message

Revision ID: 585808afd671
Revises: 14a905606ecc
Create Date: 2014-07-10 09:28:52.309482

"""

# revision identifiers, used by Alembic.
revision = '585808afd671'
down_revision = '14a905606ecc'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table('metrics')
    op.create_table('metrics_historical',
                    sa.Column('timestamp', sa.DateTime(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('challenge_slug', sa.String(), nullable=False),
                    sa.Column('status', sa.String(), nullable=False),
                    sa.Column('count', sa.Integer(), nullable=True),
                    sa.PrimaryKeyConstraint('timestamp',
                                            'user_id',
                                            'challenge_slug',
                                            'status')
                    )
    op.create_index('idx_metrics_challengeslug',
                    'metrics_historical',
                    ['challenge_slug'],
                    unique=False)
    op.create_index('idx_metrics_status',
                    'metrics_historical',
                    ['status'],
                    unique=False)
    op.create_index('idx_metrics_userid',
                    'metrics_historical',
                    ['user_id'],
                    unique=False)
    op.create_table('metrics_aggregate',
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('challenge_slug', sa.String(), nullable=False),
                    sa.Column('status', sa.String(), nullable=False),
                    sa.Column('count', sa.Integer(), nullable=True),
                    sa.PrimaryKeyConstraint('user_id',
                                            'challenge_slug',
                                            'status')
                    )


def downgrade():
    op.create_table('metrics',
                    sa.Column(
                        'timestamp',
                        postgresql.TIMESTAMP(),
                        autoincrement=False,
                        nullable=False),
                    sa.Column(
                        'user_id',
                        sa.INTEGER(),
                        server_default=
                        "nextval('metrics_user_id_seq'::regclass)",
                        nullable=False),
                    sa.Column(
                        'challenge_slug',
                        sa.VARCHAR(),
                        autoincrement=False,
                        nullable=False),
                    sa.Column(
                        'status',
                        sa.VARCHAR(),
                        autoincrement=False,
                        nullable=False),
                    sa.Column(
                        'count',
                        sa.INTEGER(),
                        autoincrement=False,
                        nullable=True),
                    sa.PrimaryKeyConstraint(
                        'timestamp',
                        'user_id',
                        'challenge_slug',
                        'status',
                        name=u'metrics_pkey')
                    )
    op.drop_table('metrics_aggregate')
    op.drop_index('idx_metrics_userid', table_name='metrics_historical')
    op.drop_index('idx_metrics_status', table_name='metrics_historical')
    op.drop_index('idx_metrics_challengeslug', table_name='metrics_historical')
    op.drop_table('metrics_historical')

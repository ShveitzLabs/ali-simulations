"""session overview

Revision ID: 0011_session_overview
Revises: 0010_evaluation_narratives
"""
from alembic import op
import sqlalchemy as sa
revision='0011_session_overview'
down_revision='0010_evaluation_narratives'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('sessions', sa.Column('overview', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('sessions','overview')

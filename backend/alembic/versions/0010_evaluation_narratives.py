"""evaluation narratives per capability

Revision ID: 0010_evaluation_narratives
Revises: 0009_peer_feedback_handoff_team
"""
from alembic import op
import sqlalchemy as sa
revision='0010_evaluation_narratives'
down_revision='0009_peer_feedback_handoff_team'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('leadership_evaluations', sa.Column('criteria_narratives_json', sa.Text(), nullable=True))
    op.add_column('leadership_peer_feedback', sa.Column('criteria_narratives_json', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('leadership_peer_feedback','criteria_narratives_json')
    op.drop_column('leadership_evaluations','criteria_narratives_json')

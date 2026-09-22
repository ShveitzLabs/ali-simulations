"""peer feedback and team-scoped handoffs

Revision ID: 0009_peer_feedback_handoff_team
Revises: 0008_leadership_development
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0009_peer_feedback_handoff_team'
down_revision='0008_leadership_development'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('session_handoffs', sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_session_handoffs_team','session_handoffs','session_teams',['team_id'],['id'])
    op.create_index('ix_session_handoffs_team_id','session_handoffs',['team_id'])
    op.create_table('leadership_peer_feedback',
        sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column('session_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('sessions.id'),nullable=False),
        sa.Column('participant_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),
        sa.Column('evaluator_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),
        sa.Column('scores_json',sa.Text(),nullable=False),sa.Column('note',sa.Text(),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_peer_feedback_session','leadership_peer_feedback',['session_id'])
    op.create_index('ix_peer_feedback_participant','leadership_peer_feedback',['participant_person_id'])
    op.create_index('ix_peer_feedback_evaluator','leadership_peer_feedback',['evaluator_person_id'])

def downgrade():
    op.drop_table('leadership_peer_feedback')
    op.drop_index('ix_session_handoffs_team_id',table_name='session_handoffs')
    op.drop_constraint('fk_session_handoffs_team','session_handoffs',type_='foreignkey')
    op.drop_column('session_handoffs','team_id')

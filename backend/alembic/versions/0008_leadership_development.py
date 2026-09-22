"""leadership development
Revision ID: 0008_leadership_development
Revises: 0007_session_workspace
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0008_leadership_development'; down_revision='0007_session_workspace'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('leadership_evaluations',
      sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('session_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('sessions.id'),nullable=False),
      sa.Column('participant_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),sa.Column('evaluator_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),
      sa.Column('context',sa.String(40),nullable=False,server_default='general'),sa.Column('scores_json',sa.Text(),nullable=False),sa.Column('strength_narrative',sa.Text(),nullable=False),sa.Column('growth_narrative',sa.Text(),nullable=False),sa.Column('evidence_notes',sa.Text()),sa.Column('status',sa.String(30),nullable=False,server_default='submitted'),
      sa.Column('approved_by_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id')),sa.Column('approved_at',sa.DateTime(timezone=True)),sa.Column('released_by_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id')),sa.Column('released_at',sa.DateTime(timezone=True)),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    for c in ('session_id','participant_person_id','evaluator_person_id','status','created_at'): op.create_index(f'ix_leadership_evaluations_{c}','leadership_evaluations',[c])
    op.create_table('leadership_observations',sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('session_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('sessions.id'),nullable=False),sa.Column('participant_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),sa.Column('observer_person_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('people.id'),nullable=False),sa.Column('capability_key',sa.String(80),nullable=False),sa.Column('context',sa.String(40),nullable=False,server_default='general'),sa.Column('note',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    for c in ('session_id','participant_person_id','observer_person_id','created_at'): op.create_index(f'ix_leadership_observations_{c}','leadership_observations',[c])
def downgrade():
    op.drop_table('leadership_observations');op.drop_table('leadership_evaluations')

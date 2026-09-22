"""template configuration for v0.8.1
Revision ID: 0005_template_configuration
Revises: 0004_templates_sessions_consent
"""
from alembic import op
import sqlalchemy as sa
revision='0005_template_configuration'; down_revision='0004_templates_sessions_consent'; branch_labels=None; depends_on=None

def upgrade():
    op.add_column('program_templates', sa.Column('configuration_json', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('program_templates','configuration_json')

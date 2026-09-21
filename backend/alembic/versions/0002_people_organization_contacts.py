"""people and organization contact fields

Revision ID: 0002_people_org_contacts
Revises: 0001_core_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_people_org_contacts"
down_revision = "0001_core_foundation"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("organizations", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("organizations", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("people", sa.Column("phone", sa.String(length=40), nullable=True))

def downgrade():
    op.drop_column("people", "phone")
    op.drop_column("organizations", "phone")
    op.drop_column("organizations", "email")

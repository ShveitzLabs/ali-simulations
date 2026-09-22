"""v0.8.2 identity access consent hardening"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0006_identity_access_consent"
down_revision="0005_template_configuration"
branch_labels=None
depends_on=None
def upgrade():
 op.add_column("people",sa.Column("birth_month",sa.Integer(),nullable=True)); op.add_column("people",sa.Column("birth_year",sa.Integer(),nullable=True))
 op.add_column("consent_templates",sa.Column("requires_renewal",sa.Boolean(),nullable=False,server_default=sa.true()))
 op.alter_column("consent_records","session_id",existing_type=postgresql.UUID(as_uuid=True),nullable=True)
 op.create_table("person_organization_contacts",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("person_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("people.id"),nullable=False),sa.Column("organization_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("organizations.id"),nullable=False),sa.Column("email",sa.String(320)),sa.Column("phone",sa.String(40)),sa.Column("supplied_by_person_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("people.id")),sa.Column("source",sa.String(30),nullable=False,server_default="organization"),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.UniqueConstraint("person_id","organization_id"))
 op.create_index("ix_poc_person","person_organization_contacts",["person_id"]); op.create_index("ix_poc_org","person_organization_contacts",["organization_id"])
 import uuid
 cid=str(uuid.uuid4())
 consent=("I authorize participation in ALI Simulations programs and activities. I understand that the program may collect and use information needed to administer participation, document leadership activities, provide evaluation and feedback, and maintain a longitudinal leadership-development record. I understand that program activities may include interaction with staff, volunteers, community partners, and evaluators; program communications; photography, audio, or video; and the ordinary risks associated with participation in educational and community activities. I acknowledge that I have had the opportunity to review this consent before agreeing to it.")
 op.execute(sa.text("INSERT INTO consent_templates (id, organization_id, name, version, body, is_active, requires_renewal) VALUES (:id, NULL, :name, 1, :body, true, true)").bindparams(id=cid,name="ALI Simulations Participation Consent",body=consent))
def downgrade():
 op.drop_index("ix_poc_org",table_name="person_organization_contacts"); op.drop_index("ix_poc_person",table_name="person_organization_contacts"); op.drop_table("person_organization_contacts")
 op.alter_column("consent_records","session_id",existing_type=postgresql.UUID(as_uuid=True),nullable=False); op.drop_column("consent_templates","requires_renewal"); op.drop_column("people","birth_year"); op.drop_column("people","birth_month")

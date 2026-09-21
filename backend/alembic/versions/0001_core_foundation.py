"""core foundation

Revision ID: 0001_core_foundation
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_core_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

license_status = postgresql.ENUM("active", "suspended", "expired", "trial", name="licensestatus", create_type=False)
simulation_lifecycle = postgresql.ENUM("development", "pilot", "available", "retired", name="simulationlifecycle", create_type=False)
scenario_status = postgresql.ENUM("draft", "testing", "published", "retired", name="scenariostatus", create_type=False)
session_mode = postgresql.ENUM("development", "production", name="sessionmode", create_type=False)

def upgrade():
    bind = op.get_bind()
    license_status.create(bind, checkfirst=True); simulation_lifecycle.create(bind, checkfirst=True); scenario_status.create(bind, checkfirst=True); session_mode.create(bind, checkfirst=True)
    op.create_table("people", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("email", sa.String(320), nullable=False), sa.Column("normalized_email", sa.String(320), nullable=False), sa.Column("first_name", sa.String(120), nullable=False), sa.Column("last_name", sa.String(120), nullable=False), sa.Column("password_hash", sa.String(255)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_people_normalized_email", "people", ["normalized_email"], unique=True); op.create_index("ix_people_is_platform_admin", "people", ["is_platform_admin"])
    op.create_table("organizations", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(200), nullable=False, unique=True), sa.Column("license_status", license_status, nullable=False, server_default="active"), sa.Column("license_started_at", sa.DateTime(timezone=True)), sa.Column("license_expires_at", sa.DateTime(timezone=True)), sa.Column("logo_url", sa.Text()), sa.Column("title", sa.String(200)), sa.Column("tagline", sa.String(300)), sa.Column("subscript", sa.String(500)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("roles", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("key", sa.String(80), nullable=False, unique=True), sa.Column("name", sa.String(120), nullable=False))
    op.create_table("permissions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("key", sa.String(120), nullable=False, unique=True), sa.Column("description", sa.String(500), nullable=False))
    op.create_table("simulation_types", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("key", sa.String(80), nullable=False, unique=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("lifecycle", simulation_lifecycle, nullable=False, server_default="development"))
    op.create_table("organization_memberships", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id"), nullable=False), sa.Column("access_expires_at", sa.DateTime(timezone=True)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("organization_id", "person_id"))
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"]); op.create_index("ix_organization_memberships_person_id", "organization_memberships", ["person_id"])
    op.create_table("membership_roles", sa.Column("membership_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization_memberships.id"), primary_key=True), sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), primary_key=True), sa.UniqueConstraint("membership_id", "role_id"))
    op.create_table("role_permissions", sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), primary_key=True), sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id"), primary_key=True), sa.UniqueConstraint("role_id", "permission_id"))
    op.create_table("organization_simulation_access", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("simulation_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_types.id"), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("access_started_at", sa.DateTime(timezone=True)), sa.Column("access_expires_at", sa.DateTime(timezone=True)), sa.Column("enabled_by_person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id")), sa.UniqueConstraint("organization_id", "simulation_type_id"))
    op.create_table("scenarios", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("simulation_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_types.id"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()))
    op.create_table("scenario_versions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id"), nullable=False), sa.Column("version", sa.String(40), nullable=False), sa.Column("status", scenario_status, nullable=False, server_default="draft"), sa.Column("published_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("scenario_id", "version"))
    op.create_table("sessions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("simulation_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_types.id"), nullable=False), sa.Column("scenario_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenario_versions.id")), sa.Column("name", sa.String(200), nullable=False), sa.Column("mode", session_mode, nullable=False, server_default="production"), sa.Column("is_development", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("starts_at", sa.DateTime(timezone=True)), sa.Column("ends_at", sa.DateTime(timezone=True)))
    op.create_index("ix_sessions_organization_id", "sessions", ["organization_id"]); op.create_index("ix_sessions_is_development", "sessions", ["is_development"])
    op.create_table("audit_events", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")), sa.Column("actor_person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("people.id")), sa.Column("action", sa.String(160), nullable=False), sa.Column("entity_type", sa.String(120), nullable=False), sa.Column("entity_id", sa.String(100)), sa.Column("detail_json", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"]); op.create_index("ix_audit_events_actor_person_id", "audit_events", ["actor_person_id"]); op.create_index("ix_audit_events_action", "audit_events", ["action"]); op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

def downgrade():
    for table in ["audit_events","sessions","scenario_versions","scenarios","organization_simulation_access","role_permissions","membership_roles","organization_memberships","simulation_types","permissions","roles","organizations","people"]:
        op.drop_table(table)
    bind = op.get_bind(); session_mode.drop(bind, checkfirst=True); scenario_status.drop(bind, checkfirst=True); simulation_lifecycle.drop(bind, checkfirst=True); license_status.drop(bind, checkfirst=True)

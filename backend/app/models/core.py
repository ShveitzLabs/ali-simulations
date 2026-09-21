import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class LicenseStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    expired = "expired"
    trial = "trial"

class SimulationLifecycle(str, enum.Enum):
    development = "development"
    pilot = "pilot"
    available = "available"
    retired = "retired"

class ScenarioStatus(str, enum.Enum):
    draft = "draft"
    testing = "testing"
    published = "published"
    retired = "retired"

class SessionMode(str, enum.Enum):
    development = "development"
    production = "production"

class Person(Base):
    __tablename__ = "people"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    license_status: Mapped[LicenseStatus] = mapped_column(Enum(LicenseStatus), default=LicenseStatus.active, nullable=False)
    license_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    license_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    logo_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(200))
    tagline: Mapped[str | None] = mapped_column(String(300))
    subscript: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "person_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.id"), nullable=False, index=True)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

class MembershipRole(Base):
    __tablename__ = "membership_roles"
    __table_args__ = (UniqueConstraint("membership_id", "role_id"),)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization_memberships.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"), primary_key=True)

class SimulationType(Base):
    __tablename__ = "simulation_types"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    lifecycle: Mapped[SimulationLifecycle] = mapped_column(Enum(SimulationLifecycle), default=SimulationLifecycle.development)

class OrganizationSimulationAccess(Base):
    __tablename__ = "organization_simulation_access"
    __table_args__ = (UniqueConstraint("organization_id", "simulation_type_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    simulation_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_types.id"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled_by_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("people.id"))

class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_types.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[ScenarioStatus] = mapped_column(Enum(ScenarioStatus), default=ScenarioStatus.draft)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    simulation_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_types.id"), nullable=False)
    scenario_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenario_versions.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[SessionMode] = mapped_column(Enum(SessionMode), default=SessionMode.production, nullable=False)
    is_development: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("people.id"), index=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    detail_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

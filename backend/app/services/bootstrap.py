from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..models.core import Person, Role, Permission, RolePermission
from ..auth.security import hash_password

ROLE_NAMES = {
    "platform_admin": "Platform Administrator",
    "organization_admin": "Organization Administrator",
    "organization_viewer": "Organization Viewer",
    "session_admin": "Session Administrator",
    "simulation_staff": "Simulation Leadership Staff",
    "evaluator": "Evaluator / Judge",
    "participant": "Participant",
    "facilitator": "Facilitator / Volunteer",
}
PERMISSIONS = {
    "organization.view": "View organizations within authorized scope",
    "organization.edit": "Edit organization settings",
    "organization.license.manage": "Manage organization licensing and expiration",
    "simulation.entitlement.manage": "Enable or disable simulation access by organization",
    "scenario.view": "View available scenarios",
    "scenario.design": "Create and edit scenario content",
    "scenario.test": "Run development/test scenarios",
    "scenario.publish": "Publish or retire scenario versions",
    "session.create": "Create sessions",
    "session.manage": "Manage assigned sessions",
    "session.operate": "Operate a live simulation",
    "people.manage": "Manage people and organization memberships",
    "observation.create": "Create participant observations",
    "evaluation.create": "Submit assigned evaluations",
    "evaluation.approve": "Approve feedback except own submissions",
    "evaluation.release": "Release approved feedback except own submissions",
    "consent.manage": "Manage participation consent workflows",
    "communication.send": "Send authorized communications",
    "report.view": "View authorized reports",
    "report.export_summary": "Export curated summary/outcome data",
    "branding.edit": "Edit authorized branding",
    "audit.view": "View authorized audit history",
}

def seed_core(db: Session):
    for key, name in ROLE_NAMES.items():
        if not db.scalar(select(Role).where(Role.key == key)):
            db.add(Role(key=key, name=name))
    for key, description in PERMISSIONS.items():
        if not db.scalar(select(Permission).where(Permission.key == key)):
            db.add(Permission(key=key, description=description))
    db.commit()
    platform = db.scalar(select(Role).where(Role.key == "platform_admin"))
    for perm in db.scalars(select(Permission)).all():
        exists = db.scalar(select(RolePermission).where(RolePermission.role_id == platform.id, RolePermission.permission_id == perm.id))
        if not exists:
            db.add(RolePermission(role_id=platform.id, permission_id=perm.id))
    db.commit()

    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        email = settings.bootstrap_admin_email.strip().lower()
        person = db.scalar(select(Person).where(Person.normalized_email == email))
        if not person:
            db.add(Person(email=settings.bootstrap_admin_email, normalized_email=email,
                          first_name=settings.bootstrap_admin_first_name, last_name=settings.bootstrap_admin_last_name,
                          password_hash=hash_password(settings.bootstrap_admin_password), is_active=True,
                          is_platform_admin=True, must_change_password=True))
            db.commit()

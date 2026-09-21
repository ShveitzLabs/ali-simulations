import json
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import (
    Person, Organization, OrganizationMembership, MembershipRole, Role,
    SimulationType, OrganizationSimulationAccess, AuditEvent,
    Session as SimulationSession, LicenseStatus
)

router = APIRouter(prefix="/api/platform", tags=["platform"])

def require_platform_admin(person: Person = Depends(get_current_person)):
    if not person.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform administrator access required")
    return person

def audit(db, actor, action, entity_type, entity_id=None, organization_id=None, detail=None):
    db.add(AuditEvent(organization_id=organization_id, actor_person_id=actor.id, action=action,
        entity_type=entity_type, entity_id=str(entity_id) if entity_id else None,
        detail_json=json.dumps(detail or {}, default=str)))

def commit_or_500(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That record conflicts with existing platform data. Check the organization name or email and try again.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=message) from exc

class AdministratorIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr

class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    license_status: LicenseStatus = LicenseStatus.active
    license_started_at: datetime | None = None
    license_expires_at: datetime | None = None
    title: str | None = None
    tagline: str | None = None
    subscript: str | None = None
    logo_url: str | None = None
    is_active: bool = True
    initial_admin: AdministratorIn | None = None

class PersonIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool = True

def org_out(o):
    return {"id":str(o.id),"name":o.name,"email":o.email,"phone":o.phone,
        "license_status":o.license_status.value,"license_started_at":o.license_started_at,
        "license_expires_at":o.license_expires_at,"title":o.title,"tagline":o.tagline,
        "subscript":o.subscript,"logo_url":o.logo_url,"is_active":o.is_active}

def person_out(p, db):
    memberships=[]
    rows=db.execute(
        select(OrganizationMembership, Organization)
        .join(Organization, Organization.id==OrganizationMembership.organization_id)
        .where(OrganizationMembership.person_id==p.id)
        .order_by(Organization.name)
    ).all()
    for m,o in rows:
        role_names=db.scalars(
            select(Role.name).join(MembershipRole, MembershipRole.role_id==Role.id)
            .where(MembershipRole.membership_id==m.id)
        ).all()
        memberships.append({"membership_id":str(m.id),"organization_id":str(o.id),
            "organization_name":o.name,"is_active":m.is_active,
            "access_expires_at":m.access_expires_at,"roles":list(role_names)})
    return {"id":str(p.id),"first_name":p.first_name,"last_name":p.last_name,
        "email":p.email,"phone":p.phone,"is_active":p.is_active,
        "is_platform_admin":p.is_platform_admin,"has_account":bool(p.password_hash),
        "memberships":memberships,"created_at":p.created_at}

def ensure_org_admin(db, organization_id, admin: AdministratorIn):
    email=admin.email.strip().lower()
    p=db.scalar(select(Person).where(Person.normalized_email==email))
    if not p:
        p=Person(email=admin.email.strip(),normalized_email=email,
                 first_name=admin.first_name.strip(),last_name=admin.last_name.strip(),
                 is_active=True,is_platform_admin=False)
        db.add(p); db.flush()
    m=db.scalar(select(OrganizationMembership).where(
        OrganizationMembership.organization_id==organization_id,
        OrganizationMembership.person_id==p.id))
    if not m:
        m=OrganizationMembership(organization_id=organization_id,person_id=p.id,is_active=True)
        db.add(m); db.flush()
    role=db.scalar(select(Role).where(Role.key=="organization_admin"))
    if not role:
        raise HTTPException(500,"Organization Administrator role is not configured.")
    if not db.scalar(select(MembershipRole).where(MembershipRole.membership_id==m.id,MembershipRole.role_id==role.id)):
        db.add(MembershipRole(membership_id=m.id,role_id=role.id))
    return p,m

@router.get("/dashboard")
def dashboard(db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    return {"organizations":db.scalar(select(func.count()).select_from(Organization)) or 0,
            "people":db.scalar(select(func.count()).select_from(Person)) or 0,
            "sessions":db.scalar(select(func.count()).select_from(SimulationSession)) or 0,
            "simulations":db.scalar(select(func.count()).select_from(SimulationType)) or 0}

@router.get("/organizations")
def organizations(db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    return [org_out(x) for x in db.scalars(select(Organization).order_by(Organization.name)).all()]

@router.post("/organizations", status_code=201)
def create_organization(body: OrganizationIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    name=body.name.strip()
    if db.scalar(select(Organization).where(func.lower(Organization.name)==name.lower())):
        raise HTTPException(409, "An organization with this name already exists.")
    values=body.model_dump(exclude={"initial_admin"})
    values["name"]=name
    o=Organization(**values)
    db.add(o)
    try:
        db.flush()
        admin_person=None
        if body.initial_admin:
            admin_person,_=ensure_org_admin(db,o.id,body.initial_admin)
        audit(db,person,"organization.create","organization",o.id,o.id,
              {"name":o.name,"initial_admin_person_id":str(admin_person.id) if admin_person else None})
        commit_or_500(db,"The organization could not be saved. No data was lost; please try again or check the server log.")
        db.refresh(o)
        return org_out(o)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Organization setup failed ({type(exc).__name__}). Check the server log for details.") from exc

@router.get("/organizations/{organization_id}")
def get_organization(organization_id: UUID, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    o=db.get(Organization,organization_id)
    if not o: raise HTTPException(404,"Organization not found")
    return org_out(o)

@router.put("/organizations/{organization_id}")
def update_organization(organization_id: UUID, body: OrganizationIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    o=db.get(Organization,organization_id)
    if not o: raise HTTPException(404,"Organization not found")
    duplicate=db.scalar(select(Organization).where(func.lower(Organization.name)==body.name.strip().lower(),Organization.id!=o.id))
    if duplicate: raise HTTPException(409,"Another organization already uses this name.")
    before=org_out(o)
    for k,v in body.model_dump(exclude={"initial_admin"}).items(): setattr(o,k,v)
    o.name=body.name.strip()
    if body.initial_admin: ensure_org_admin(db,o.id,body.initial_admin)
    audit(db,person,"organization.update","organization",o.id,o.id,{"before":before,"after":org_out(o)})
    commit_or_500(db,"The organization changes could not be saved.")
    db.refresh(o); return org_out(o)

@router.get("/people")
def people(q: str | None=None, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    stmt=select(Person).order_by(Person.last_name,Person.first_name)
    if q and q.strip():
        term=f"%{q.strip().lower()}%"
        stmt=stmt.where(
            func.lower(Person.first_name+" "+Person.last_name).like(term) |
            func.lower(Person.email).like(term))
    return [person_out(x,db) for x in db.scalars(stmt).all()]

@router.post("/people", status_code=201)
def create_person(body: PersonIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    email=body.email.strip().lower()
    if db.scalar(select(Person).where(Person.normalized_email==email)):
        raise HTTPException(409,"A person with this email address already exists. Open the existing person instead.")
    p=Person(email=body.email.strip(),normalized_email=email,first_name=body.first_name.strip(),
             last_name=body.last_name.strip(),phone=body.phone,is_active=body.is_active,is_platform_admin=False)
    db.add(p); db.flush()
    audit(db,person,"person.create","person",p.id,detail={"email":p.email})
    commit_or_500(db,"The person could not be saved.")
    db.refresh(p); return person_out(p,db)

@router.get("/people/{person_id}")
def get_person(person_id: UUID, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    p=db.get(Person,person_id)
    if not p: raise HTTPException(404,"Person not found")
    return person_out(p,db)

@router.put("/people/{person_id}")
def update_person(person_id: UUID, body: PersonIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    p=db.get(Person,person_id)
    if not p: raise HTTPException(404,"Person not found")
    email=body.email.strip().lower()
    duplicate=db.scalar(select(Person).where(Person.normalized_email==email,Person.id!=p.id))
    if duplicate: raise HTTPException(409,"Another person already uses this email address.")
    before={"first_name":p.first_name,"last_name":p.last_name,"email":p.email,"phone":p.phone,"is_active":p.is_active}
    p.first_name=body.first_name.strip();p.last_name=body.last_name.strip();p.email=body.email.strip()
    p.normalized_email=email;p.phone=body.phone;p.is_active=body.is_active
    audit(db,person,"person.update","person",p.id,detail={"before":before,"after":body.model_dump()})
    commit_or_500(db,"The person changes could not be saved.")
    db.refresh(p); return person_out(p,db)

@router.get("/simulations")
def simulations(db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    return [{"id":str(x.id),"key":x.key,"name":x.name,"lifecycle":x.lifecycle.value} for x in db.scalars(select(SimulationType).order_by(SimulationType.name)).all()]

@router.get("/organizations/{organization_id}/entitlements")
def entitlements(organization_id: UUID, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    if not db.get(Organization,organization_id): raise HTTPException(404,"Organization not found")
    sims=db.scalars(select(SimulationType).order_by(SimulationType.name)).all()
    access={x.simulation_type_id:x for x in db.scalars(select(OrganizationSimulationAccess).where(OrganizationSimulationAccess.organization_id==organization_id)).all()}
    return [{"simulation_type_id":str(s.id),"key":s.key,"name":s.name,"lifecycle":s.lifecycle.value,"enabled":bool(access.get(s.id) and access[s.id].enabled)} for s in sims]

class EntitlementIn(BaseModel): enabled: bool
@router.put("/organizations/{organization_id}/entitlements/{simulation_type_id}")
def set_entitlement(organization_id: UUID, simulation_type_id: UUID, body: EntitlementIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    if not db.get(Organization,organization_id) or not db.get(SimulationType,simulation_type_id): raise HTTPException(404,"Organization or simulation not found")
    x=db.scalar(select(OrganizationSimulationAccess).where(OrganizationSimulationAccess.organization_id==organization_id,OrganizationSimulationAccess.simulation_type_id==simulation_type_id))
    if not x:
        x=OrganizationSimulationAccess(organization_id=organization_id,simulation_type_id=simulation_type_id); db.add(x); db.flush()
    x.enabled=body.enabled; x.enabled_by_person_id=person.id; x.access_started_at=datetime.now(timezone.utc) if body.enabled else x.access_started_at
    audit(db,person,"simulation.entitlement.update","organization_simulation_access",x.id,organization_id,{"simulation_type_id":simulation_type_id,"enabled":body.enabled})
    commit_or_500(db,"Simulation access could not be updated.")
    return {"enabled":x.enabled}

@router.get("/audit")
def audit_events(limit:int=50, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    rows=db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit,200))).all()
    return [{"id":str(x.id),"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"created_at":x.created_at,"detail":json.loads(x.detail_json or "{}") } for x in rows]

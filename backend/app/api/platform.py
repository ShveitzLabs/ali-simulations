import json
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import Person, Organization, SimulationType, OrganizationSimulationAccess, AuditEvent, Session as SimulationSession, LicenseStatus

router = APIRouter(prefix="/api/platform", tags=["platform"])

def require_platform_admin(person: Person = Depends(get_current_person)):
    if not person.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform administrator access required")
    return person

def audit(db, actor, action, entity_type, entity_id=None, organization_id=None, detail=None):
    db.add(AuditEvent(organization_id=organization_id, actor_person_id=actor.id, action=action,
        entity_type=entity_type, entity_id=str(entity_id) if entity_id else None,
        detail_json=json.dumps(detail or {}, default=str)))

class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    license_status: LicenseStatus = LicenseStatus.active
    license_started_at: datetime | None = None
    license_expires_at: datetime | None = None
    title: str | None = None
    tagline: str | None = None
    subscript: str | None = None
    logo_url: str | None = None
    is_active: bool = True

def org_out(o):
    return {"id":str(o.id),"name":o.name,"license_status":o.license_status.value,"license_started_at":o.license_started_at,
        "license_expires_at":o.license_expires_at,"title":o.title,"tagline":o.tagline,"subscript":o.subscript,"logo_url":o.logo_url,"is_active":o.is_active}

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
    if db.scalar(select(Organization).where(func.lower(Organization.name)==body.name.strip().lower())):
        raise HTTPException(409, "An organization with this name already exists")
    o=Organization(**body.model_dump(), name=body.name.strip())
    db.add(o); db.flush(); audit(db,person,"organization.create","organization",o.id,o.id,{"name":o.name}); db.commit(); db.refresh(o)
    return org_out(o)

@router.get("/organizations/{organization_id}")
def get_organization(organization_id: UUID, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    o=db.get(Organization,organization_id)
    if not o: raise HTTPException(404,"Organization not found")
    return org_out(o)

@router.put("/organizations/{organization_id}")
def update_organization(organization_id: UUID, body: OrganizationIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    o=db.get(Organization,organization_id)
    if not o: raise HTTPException(404,"Organization not found")
    before=org_out(o)
    for k,v in body.model_dump().items(): setattr(o,k,v)
    o.name=body.name.strip(); audit(db,person,"organization.update","organization",o.id,o.id,{"before":before,"after":body.model_dump()}); db.commit(); db.refresh(o)
    return org_out(o)

@router.get("/simulations")
def simulations(db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    return [{"id":str(x.id),"key":x.key,"name":x.name,"lifecycle":x.lifecycle.value} for x in db.scalars(select(SimulationType).order_by(SimulationType.name)).all()]

@router.get("/organizations/{organization_id}/entitlements")
def entitlements(organization_id: UUID, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    sims=db.scalars(select(SimulationType).order_by(SimulationType.name)).all()
    access={x.simulation_type_id:x for x in db.scalars(select(OrganizationSimulationAccess).where(OrganizationSimulationAccess.organization_id==organization_id)).all()}
    return [{"simulation_type_id":str(s.id),"key":s.key,"name":s.name,"lifecycle":s.lifecycle.value,"enabled":bool(access.get(s.id) and access[s.id].enabled)} for s in sims]

class EntitlementIn(BaseModel): enabled: bool
@router.put("/organizations/{organization_id}/entitlements/{simulation_type_id}")
def set_entitlement(organization_id: UUID, simulation_type_id: UUID, body: EntitlementIn, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    if not db.get(Organization,organization_id) or not db.get(SimulationType,simulation_type_id): raise HTTPException(404,"Organization or simulation not found")
    x=db.scalar(select(OrganizationSimulationAccess).where(OrganizationSimulationAccess.organization_id==organization_id,OrganizationSimulationAccess.simulation_type_id==simulation_type_id))
    if not x:
        x=OrganizationSimulationAccess(organization_id=organization_id,simulation_type_id=simulation_type_id); db.add(x)
    x.enabled=body.enabled; x.enabled_by_person_id=person.id; x.access_started_at=datetime.now(timezone.utc) if body.enabled else x.access_started_at
    audit(db,person,"simulation.entitlement.update","organization_simulation_access",x.id,organization_id,{"simulation_type_id":simulation_type_id,"enabled":body.enabled}); db.commit()
    return {"enabled":x.enabled}

@router.get("/audit")
def audit_events(limit:int=50, db: Session=Depends(get_db), person: Person=Depends(require_platform_admin)):
    rows=db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit,200))).all()
    return [{"id":str(x.id),"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"created_at":x.created_at,"detail":json.loads(x.detail_json or "{}") } for x in rows]

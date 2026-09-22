from uuid import UUID as PyUUID
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,EmailStr,Field
from sqlalchemy import select,or_,func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import *

router=APIRouter(prefix="/api/content",tags=["content"])
ROLE_KEYS=["team_lead","data_analyst","logistics_traffic_flow","community_liaison","quality_control","communications_lead"]
CATEGORY_LIBRARY=[("food","Food"),("toys","Toys"),("clothing","Clothing"),("school_supplies","School Supplies"),("hygiene","Hygiene Essentials"),("winter_warmth","Winter Warmth")]
def admin(p=Depends(get_current_person)):
    if not p.is_platform_admin: raise HTTPException(403,"Platform administrator access required")
    return p
def org_ids(db,p): return set(db.scalars(select(OrganizationMembership.organization_id).where(OrganizationMembership.person_id==p.id,OrganizationMembership.is_active==True)).all())
def c_out(c): return {k:getattr(c,k) for k in ["id","scope","first_name","last_name","title","company","email","phone","notes","connection_context","future_outreach_consent","organization_id","session_id"]}
class ContactIn(BaseModel):
    first_name:str;last_name:str;title:str|None=None;company:str|None=None;email:EmailStr|None=None;phone:str|None=None;notes:str|None=None;connection_context:str|None=None;future_outreach_consent:bool=False;scope:str="personal";organization_id:PyUUID | None=None;session_id:PyUUID | None=None
@router.get("/contacts")
def contacts(q:str|None=None,scope:str|None=None,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    ids=org_ids(db,p); cond=[Contact.owner_person_id==p.id]
    if ids: cond.append(Contact.organization_id.in_(ids))
    stmt=select(Contact).where(Contact.is_active==True,or_(*cond))
    if scope: stmt=stmt.where(Contact.scope==scope)
    if q:
        x=f"%{q.strip().lower()}%"; cols=[Contact.first_name,Contact.last_name,Contact.title,Contact.company,Contact.email,Contact.phone,Contact.connection_context]
        stmt=stmt.where(or_(*[func.lower(func.coalesce(c,"" )).like(x) for c in cols]))
    out=[c_out(c) for c in db.scalars(stmt.order_by(Contact.last_name,Contact.first_name)).all()]
    # Active platform people in the participant's organizations are automatic organization contacts.
    if ids and (not scope or scope=="organization"):
        rows=db.execute(select(Person,OrganizationMembership,Organization).join(OrganizationMembership,OrganizationMembership.person_id==Person.id).join(Organization,Organization.id==OrganizationMembership.organization_id).where(OrganizationMembership.organization_id.in_(ids),OrganizationMembership.is_active==True,Person.is_active==True)).all()
        existing={(str(x.get("email") or "").lower(),x.get("scope")) for x in out}
        for person,membership,org in rows:
            key=(person.email.lower(),"organization")
            if key not in existing:
                out.append({"id":f"person:{person.id}:{org.id}","scope":"organization","first_name":person.first_name,"last_name":person.last_name,"title":None,"company":org.name,"email":person.email,"phone":person.phone,"notes":None,"connection_context":"Organization contact","future_outreach_consent":False,"organization_id":org.id,"session_id":None})
                existing.add(key)
    if q:
        term=q.strip().lower(); searchable=("first_name","last_name","title","company","email","phone","connection_context")
        out=[x for x in out if any(term in str(x.get(k) or "").lower() for k in searchable)]
    return sorted(out,key=lambda x:(str(x.get("last_name") or "").lower(),str(x.get("first_name") or "").lower()))
@router.post("/contacts",status_code=201)
def add_contact(b:ContactIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if b.scope!="personal" and not p.is_platform_admin: raise HTTPException(403,"Only administrators can create shared contacts")
    c=Contact(**b.model_dump(),owner_person_id=p.id if b.scope=="personal" else None,created_by_person_id=p.id);db.add(c);db.commit();db.refresh(c);return c_out(c)
@router.delete("/contacts/{cid}",status_code=204)
def del_contact(cid:PyUUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    c=db.get(Contact,cid)
    if not c or (c.owner_person_id!=p.id and not p.is_platform_admin): raise HTTPException(404,"Contact not found")
    c.is_active=False;db.commit()

class PartnerIn(BaseModel): name:str;organization_id:UUID;description:str|None=None;email:EmailStr|None=None;phone:str|None=None
@router.get("/partners")
def partners(db:Session=Depends(get_db),p:Person=Depends(admin)):
    return [{"id":x.id,"organization_id":x.organization_id,"name":x.name,"description":x.description,"email":x.email,"phone":x.phone,"is_active":x.is_active} for x in db.scalars(select(CommunityPartner).order_by(CommunityPartner.name)).all()]
@router.post("/partners",status_code=201)
def partner_add(b:PartnerIn,db:Session=Depends(get_db),p:Person=Depends(admin)):
    x=CommunityPartner(**b.model_dump());db.add(x);db.commit();db.refresh(x);return {"id":x.id,"name":x.name}

class ChallengeIn(BaseModel): name:str;organization_id:UUID;community_partner_id:PyUUID | None=None;description:str|None=None;starts_at:datetime|None=None;ends_at:datetime|None=None;categories:list[str]=Field(default_factory=lambda:["food"])
@router.get("/belonging/library")
def library(p:Person=Depends(get_current_person)):
    return {"framework":["VOICE","CHOICE","AGENCY","IMPACT"],"categories":[{"key":k,"name":n} for k,n in CATEGORY_LIBRARY]+[{"key":"custom","name":"Other / Custom"}],"roles":ROLE_KEYS}
@router.get("/belonging/challenges")
def challenges(db:Session=Depends(get_db),p:Person=Depends(admin)):
    out=[]
    for x in db.scalars(select(BelongingChallenge).order_by(BelongingChallenge.created_at.desc())).all():
        cats=db.scalars(select(CollectionCategory).where(CollectionCategory.challenge_id==x.id)).all(); teams=db.scalars(select(ChallengeTeam).where(ChallengeTeam.challenge_id==x.id)).all()
        out.append({"id":x.id,"name":x.name,"organization_id":x.organization_id,"community_partner_id":x.community_partner_id,"description":x.description,"status":x.status,"categories":[{"id":c.id,"key":c.key,"name":c.name,"unit":c.unit,"monetary_enabled":c.monetary_enabled,"priority":c.priority} for c in cats],"teams":[{"id":t.id,"name":t.name} for t in teams]})
    return out
@router.post("/belonging/challenges",status_code=201)
def challenge_add(b:ChallengeIn,db:Session=Depends(get_db),p:Person=Depends(admin)):
    x=BelongingChallenge(**b.model_dump(exclude={"categories"}));db.add(x);db.flush(); names=dict(CATEGORY_LIBRARY)
    for k in b.categories:
        db.add(CollectionCategory(challenge_id=x.id,key=k,name=names.get(k,"Custom Collection"),monetary_enabled=True))
    db.add_all([ChallengeTeam(challenge_id=x.id,name="Team A"),ChallengeTeam(challenge_id=x.id,name="Team B")]);db.commit();db.refresh(x);return {"id":x.id,"name":x.name}
class TxIn(BaseModel): challenge_id:UUID;team_id:PyUUID | None=None;category_id:PyUUID | None=None;contribution_type:str;subcategory:str|None=None;quantity:str|None=None;amount:str|None=None;donor_name:str|None=None;designation:str|None=None;qc_status:str="pending";notes:str|None=None
@router.post("/belonging/collections",status_code=201)
def tx_add(b:TxIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if b.contribution_type not in ("in_kind","monetary"): raise HTTPException(400,"Contribution type must be in_kind or monetary")
    x=CollectionTransaction(**b.model_dump(),entered_by_person_id=p.id);db.add(x);db.commit();db.refresh(x);return {"id":x.id}
@router.get("/belonging/collections/{challenge_id}")
def tx_list(challenge_id:PyUUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    xs=db.scalars(select(CollectionTransaction).where(CollectionTransaction.challenge_id==challenge_id).order_by(CollectionTransaction.created_at.desc())).all()
    return [{k:getattr(x,k) for k in ["id","team_id","category_id","contribution_type","subcategory","quantity","amount","donor_name","designation","qc_status","notes","created_at"]} for x in xs]
class OutreachIn(BaseModel): challenge_id:UUID;team_id:PyUUID | None=None;activity_type:str;contact_name:str|None=None;organization_name:str|None=None;outcome:str|None=None;notes:str|None=None
@router.post("/belonging/outreach",status_code=201)
def outreach_add(b:OutreachIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    x=OutreachActivity(**b.model_dump(),entered_by_person_id=p.id);db.add(x);db.commit();return {"id":x.id}

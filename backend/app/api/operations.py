import json, random
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import Person,Organization,OrganizationMembership,MembershipRole,Role,SimulationType,OrganizationSimulationAccess,ProgramTemplate,Session as ProgramSession,SessionTeam,SessionParticipant,SessionRoleAssignment,ConsentTemplate,ConsentRecord,AuditEvent
router=APIRouter(prefix='/api/operations',tags=['operations'])

def memberships(db,p):
    rows=db.execute(select(OrganizationMembership,Role).join(MembershipRole,MembershipRole.membership_id==OrganizationMembership.id).join(Role,Role.id==MembershipRole.role_id).where(OrganizationMembership.person_id==p.id,OrganizationMembership.is_active==True)).all()
    return [(m,r.key) for m,r in rows]
def is_org_admin(db,p,oid): return p.is_platform_admin or any(m.organization_id==oid and r=='organization_admin' for m,r in memberships(db,p))
def require_org(db,p,oid):
    if not is_org_admin(db,p,oid): raise HTTPException(403,'Organization Administrator access required')
def log(db,p,action,etype,eid,oid,summary,detail=None): db.add(AuditEvent(organization_id=oid,actor_person_id=p.id,action=action,entity_type=etype,entity_id=str(eid),detail_json=json.dumps({'summary':summary,**(detail or {})},default=str)))

class TemplateIn(BaseModel):
    simulation_type_id:UUID; name:str=Field(min_length=2,max_length=200); description:str|None=None; default_role_key:str|None='team_member'; role_assignment_mode:str='manual_default'; max_teams:int=Field(default=4,ge=1,le=4); status:str='available'; configuration:dict=Field(default_factory=dict)
def template_out(x):
    try: config=json.loads(x.configuration_json) if x.configuration_json else {}
    except Exception: config={}
    return {'id':str(x.id),'simulation_type_id':str(x.simulation_type_id),'name':x.name,'description':x.description,'default_role_key':x.default_role_key,'role_assignment_mode':x.role_assignment_mode,'max_teams':x.max_teams,'status':x.status,'version':x.version,'archived_at':x.archived_at,'configuration':config}

@router.get('/templates')
def templates(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    xs=db.scalars(select(ProgramTemplate).order_by(ProgramTemplate.name)).all()
    if p.is_platform_admin:return [template_out(x) for x in xs]
    orgs={m.organization_id for m,_ in memberships(db,p)}
    enabled=set(db.scalars(select(OrganizationSimulationAccess.simulation_type_id).where(OrganizationSimulationAccess.organization_id.in_(orgs),OrganizationSimulationAccess.enabled==True)).all()) if orgs else set()
    return [template_out(x) for x in xs if x.status=='available' and x.simulation_type_id in enabled]
@router.post('/templates',status_code=201)
def template_create(b:TemplateIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    data=b.model_dump(exclude={'configuration'});x=ProgramTemplate(**data,configuration_json=json.dumps(b.configuration));db.add(x);db.flush();log(db,p,'template.create','program_template',x.id,None,f'Created template “{x.name}”.');db.commit();return template_out(x)
@router.put('/templates/{tid}')
def template_update(tid:UUID,b:TemplateIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    x=db.get(ProgramTemplate,tid)
    if not x:raise HTTPException(404,'Template not found')
    before=x.name
    for k,v in b.model_dump(exclude={'configuration'}).items():setattr(x,k,v)
    x.configuration_json=json.dumps(b.configuration)
    x.version+=1;log(db,p,'template.update','program_template',x.id,None,f'Updated template “{x.name}” (version {x.version}).',{'previous_name':before});db.commit();return template_out(x)
@router.delete('/templates/{tid}')
def template_archive(tid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    x=db.get(ProgramTemplate,tid)
    if not x:raise HTTPException(404,'Template not found')
    used=db.scalar(select(func.count()).select_from(ProgramSession).where(ProgramSession.template_id==x.id)) or 0
    if used:x.status='archived';x.archived_at=datetime.now(timezone.utc);summary=f'Archived template “{x.name}” because it has session history.'
    else: db.delete(x);summary=f'Deleted unused template “{x.name}”.'
    log(db,p,'template.archive' if used else 'template.delete','program_template',x.id,None,summary,{'sessions':used});db.commit();return {'ok':True,'archived':bool(used)}

@router.get('/session-options')
def session_options(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if p.is_platform_admin:
        orgs=db.scalars(select(Organization).where(Organization.is_active==True).order_by(Organization.name)).all()
    else:
        admin_org_ids={m.organization_id for m,r in memberships(db,p) if r=='organization_admin'}
        orgs=db.scalars(select(Organization).where(Organization.id.in_(admin_org_ids),Organization.is_active==True).order_by(Organization.name)).all() if admin_org_ids else []
    result=[]
    for o in orgs:
        enabled=set(db.scalars(select(OrganizationSimulationAccess.simulation_type_id).where(OrganizationSimulationAccess.organization_id==o.id,OrganizationSimulationAccess.enabled==True)).all())
        ts=db.scalars(select(ProgramTemplate).where(ProgramTemplate.status=='available',ProgramTemplate.simulation_type_id.in_(enabled)).order_by(ProgramTemplate.name)).all() if enabled else []
        result.append({'id':str(o.id),'name':o.name,'templates':[template_out(t) for t in ts]})
    return {'organizations':result}

class SessionIn(BaseModel):
    organization_id:UUID; template_id:UUID; name:str; starts_at:datetime|None=None; ends_at:datetime|None=None; team_count:int=Field(default=2,ge=1,le=4); mode:str='production'
def session_out(db,x):
    teams=db.scalars(select(SessionTeam).where(SessionTeam.session_id==x.id).order_by(SessionTeam.sort_order)).all(); count=db.scalar(select(func.count()).select_from(SessionParticipant).where(SessionParticipant.session_id==x.id,SessionParticipant.is_active==True)) or 0
    return {'id':str(x.id),'organization_id':str(x.organization_id),'template_id':str(x.template_id) if x.template_id else None,'name':x.name,'starts_at':x.starts_at,'ends_at':x.ends_at,'status':x.status,'team_count':x.team_count,'participant_count':count,'teams':[{'id':str(t.id),'name':t.name,'sort_order':t.sort_order} for t in teams]}
@router.get('/sessions')
def sessions(organization_id:UUID|None=None,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    stmt=select(ProgramSession).where(ProgramSession.template_id.is_not(None)).order_by(ProgramSession.starts_at.desc().nullslast(),ProgramSession.name)
    if p.is_platform_admin:
        if organization_id:stmt=stmt.where(ProgramSession.organization_id==organization_id)
    else:
        orgs={m.organization_id for m,_ in memberships(db,p)};stmt=stmt.where(ProgramSession.organization_id.in_(orgs))
    return [session_out(db,x) for x in db.scalars(stmt).all()]
@router.post('/sessions',status_code=201)
def session_create(b:SessionIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    require_org(db,p,b.organization_id);t=db.get(ProgramTemplate,b.template_id)
    if not t or t.status!='available':raise HTTPException(400,'Template is not available')
    access=db.scalar(select(OrganizationSimulationAccess).where(OrganizationSimulationAccess.organization_id==b.organization_id,OrganizationSimulationAccess.simulation_type_id==t.simulation_type_id,OrganizationSimulationAccess.enabled==True))
    if not access and not p.is_platform_admin:raise HTTPException(403,'Organization is not entitled to this template')
    x=ProgramSession(organization_id=b.organization_id,simulation_type_id=t.simulation_type_id,template_id=t.id,name=b.name,starts_at=b.starts_at,ends_at=b.ends_at,team_count=b.team_count,status='draft',is_development=b.mode=='development');db.add(x);db.flush()
    for i in range(b.team_count):db.add(SessionTeam(session_id=x.id,name=f'Team {chr(65+i)}',sort_order=i+1))
    log(db,p,'session.create','session',x.id,x.organization_id,f'Created session “{x.name}” from template “{t.name}” with {b.team_count} teams.');db.commit();return session_out(db,x)
class TeamPatch(BaseModel): name:str
@router.put('/sessions/{sid}/teams/{team_id}')
def team_rename(sid:UUID,team_id:UUID,b:TeamPatch,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    s=db.get(ProgramSession,sid);team=db.get(SessionTeam,team_id)
    if not s or not team or team.session_id!=s.id:raise HTTPException(404,'Team not found')
    require_org(db,p,s.organization_id);old=team.name;team.name=b.name.strip();log(db,p,'team.rename','session_team',team.id,s.organization_id,f'Renamed {old} to {team.name} in “{s.name}”.');db.commit();return {'ok':True}
class ParticipantIn(BaseModel): person_id:UUID; team_id:UUID|None=None
@router.post('/sessions/{sid}/participants')
def participant_add(sid:UUID,b:ParticipantIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    s=db.get(ProgramSession,sid);require_org(db,p,s.organization_id if s else UUID(int=0));t=db.get(ProgramTemplate,s.template_id)
    x=db.scalar(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==b.person_id))
    if not x:x=SessionParticipant(session_id=sid,person_id=b.person_id,team_id=b.team_id,current_role_key=t.default_role_key if t and t.role_assignment_mode=='manual_default' else None);db.add(x)
    else:x.is_active=True;x.team_id=b.team_id
    who=db.get(Person,b.person_id);log(db,p,'session.participant.add','session_participant',x.id,s.organization_id,f'Added {who.first_name} {who.last_name} to “{s.name}”.');db.commit();return {'ok':True}
@router.post('/sessions/{sid}/auto-balance')
def auto_balance(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    s=db.get(ProgramSession,sid);require_org(db,p,s.organization_id if s else UUID(int=0));teams=db.scalars(select(SessionTeam).where(SessionTeam.session_id==sid).order_by(SessionTeam.sort_order)).all();people=db.scalars(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.is_active==True).order_by(SessionParticipant.person_id)).all()
    if not teams:raise HTTPException(400,'No teams configured')
    random.shuffle(people)
    for i,x in enumerate(people):x.team_id=teams[i%len(teams)].id
    log(db,p,'team.auto_balance','session',s.id,s.organization_id,f'Auto-balanced {len(people)} participants across {len(teams)} teams in “{s.name}”.');db.commit();return session_out(db,s)
class AssignmentIn(BaseModel): team_id:UUID|None=None; role_key:str|None=None; reason:str|None=None
@router.put('/sessions/{sid}/participants/{pid}')
def assign(sid:UUID,pid:UUID,b:AssignmentIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    s=db.get(ProgramSession,sid);require_org(db,p,s.organization_id if s else UUID(int=0));x=db.scalar(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==pid));who=db.get(Person,pid)
    if not x:raise HTTPException(404,'Participant not found')
    if b.team_id is not None:x.team_id=b.team_id
    if b.role_key is not None and b.role_key!=x.current_role_key:
        db.query(SessionRoleAssignment).filter(SessionRoleAssignment.session_id==sid,SessionRoleAssignment.person_id==pid,SessionRoleAssignment.ended_at==None).update({'ended_at':datetime.now(timezone.utc)})
        x.current_role_key=b.role_key;db.add(SessionRoleAssignment(session_id=sid,person_id=pid,role_key=b.role_key,reason=b.reason or 'Administrator reassignment',assigned_by_person_id=p.id))
    log(db,p,'participant.assignment.update','session_participant',x.id,s.organization_id,f'Updated team/role assignment for {who.first_name} {who.last_name} in “{s.name}”.',{'role':x.current_role_key,'team_id':str(x.team_id) if x.team_id else None});db.commit();return {'ok':True}

class ConsentTemplateIn(BaseModel): organization_id:UUID|None=None; name:str; body:str
@router.get('/consent/templates')
def consent_templates(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    orgs={m.organization_id for m,_ in memberships(db,p)}
    stmt=select(ConsentTemplate).where(ConsentTemplate.is_active==True)
    if not p.is_platform_admin:stmt=stmt.where((ConsentTemplate.organization_id.in_(orgs))|(ConsentTemplate.organization_id==None))
    return [{'id':str(x.id),'organization_id':str(x.organization_id) if x.organization_id else None,'name':x.name,'version':x.version,'body':x.body} for x in db.scalars(stmt.order_by(ConsentTemplate.name)).all()]
@router.post('/consent/templates',status_code=201)
def consent_template_add(b:ConsentTemplateIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    if b.organization_id is not None:raise HTTPException(400,'Consent is managed at the platform level')
    for old in db.scalars(select(ConsentTemplate).where(ConsentTemplate.organization_id==None,ConsentTemplate.is_active==True)).all(): old.is_active=False
    prior=db.scalar(select(func.max(ConsentTemplate.version)).where(ConsentTemplate.organization_id==None)) or 0
    x=ConsentTemplate(organization_id=None,name=b.name,body=b.body,version=prior+1,is_active=True,requires_renewal=True);db.add(x);db.flush();log(db,p,'consent.template.create','consent_template',x.id,None,f'Published platform consent “{x.name}” version {x.version}.');db.commit();return {'id':str(x.id)}
class ConsentIn(BaseModel): session_id:UUID; person_id:UUID; template_id:UUID; signer_type:str; signer_name:str; signer_email:str|None=None
@router.post('/consent/records',status_code=201)
def consent_record(b:ConsentIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    s=db.get(ProgramSession,b.session_id);require_org(db,p,s.organization_id if s else UUID(int=0));x=ConsentRecord(**b.model_dump());db.add(x);db.flush();who=db.get(Person,b.person_id);log(db,p,'consent.record','consent_record',x.id,s.organization_id,f'Recorded {b.signer_type} consent for {who.first_name} {who.last_name} in “{s.name}”.');db.commit();return {'id':str(x.id)}

@router.get('/reports/summary')
def reports(organization_id:UUID|None=None,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if organization_id:require_org(db,p,organization_id)
    elif not p.is_platform_admin:
        ids=[m.organization_id for m,_ in memberships(db,p) if _=='organization_admin'];organization_id=ids[0] if ids else None
        if not organization_id:raise HTTPException(403,'Organization Administrator access required')
    cond=[] if organization_id is None else [ProgramSession.organization_id==organization_id]
    sessions=db.scalar(select(func.count()).select_from(ProgramSession).where(*cond)) or 0
    active=db.scalar(select(func.count()).select_from(ProgramSession).where(*cond,ProgramSession.status=='active')) or 0
    participants=db.scalar(select(func.count()).select_from(SessionParticipant).join(ProgramSession,ProgramSession.id==SessionParticipant.session_id).where(*cond,SessionParticipant.is_active==True)) or 0
    consents=db.scalar(select(func.count()).select_from(ConsentRecord).join(ProgramSession,ProgramSession.id==ConsentRecord.session_id).where(*cond)) or 0
    return {'sessions':sessions,'active_sessions':active,'participant_assignments':participants,'consents_recorded':consents}

@router.get('/view-as-users')
def view_as_users(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if p.is_platform_admin:
        xs=db.scalars(select(Person).where(Person.is_active==True).order_by(Person.last_name,Person.first_name)).all()
    else:
        admin_orgs={m.organization_id for m,r in memberships(db,p) if r=='organization_admin'}
        if not admin_orgs:raise HTTPException(403,'Organization Administrator access required')
        xs=db.scalars(select(Person).join(OrganizationMembership,OrganizationMembership.person_id==Person.id).where(OrganizationMembership.organization_id.in_(admin_orgs),OrganizationMembership.is_active==True,Person.is_active==True,Person.is_platform_admin==False).distinct().order_by(Person.last_name,Person.first_name)).all()
    return [{'id':str(x.id),'first_name':x.first_name,'last_name':x.last_name,'email':x.email} for x in xs]

# v0.8.2 scoped identity/access and platform-managed consent
from ..models.core import PersonOrganizationContact
from sqlalchemy import delete

DEFAULT_CONSENT_NAME='ALI Simulations Participation Consent'
class ScopedPersonIn(BaseModel):
    organization_id:UUID; first_name:str; last_name:str; email:str; phone:str|None=None; role_key:str='participant'
class MembershipPatch(BaseModel):
    role_key:str|None=None; is_active:bool=True
class PlatformRolePatch(BaseModel):
    is_platform_admin:bool

def admin_org_ids(db,p):
    return {m.organization_id for m,r in memberships(db,p) if r=='organization_admin'}
def scoped_person_out(db,p,viewer):
    if viewer.is_platform_admin:
        email,phone=p.email,p.phone
    else:
        ids=admin_org_ids(db,viewer)
        c=db.scalar(select(PersonOrganizationContact).where(PersonOrganizationContact.person_id==p.id,PersonOrganizationContact.organization_id.in_(ids))) if ids else None
        email,phone=(c.email if c else None),(c.phone if c else None)
    ms=[]
    stmt=select(OrganizationMembership,Organization).join(Organization,Organization.id==OrganizationMembership.organization_id).where(OrganizationMembership.person_id==p.id)
    if not viewer.is_platform_admin: stmt=stmt.where(OrganizationMembership.organization_id.in_(admin_org_ids(db,viewer)))
    for m,o in db.execute(stmt).all():
        rs=list(db.scalars(select(Role.key).join(MembershipRole,MembershipRole.role_id==Role.id).where(MembershipRole.membership_id==m.id)).all())
        ms.append({'membership_id':str(m.id),'organization_id':str(o.id),'organization_name':o.name,'roles':rs,'is_active':m.is_active})
    return {'id':str(p.id),'first_name':p.first_name,'last_name':p.last_name,'email':email,'phone':phone,'is_active':p.is_active,'is_platform_admin':p.is_platform_admin if viewer.is_platform_admin else False,'memberships':ms}

@router.get('/access/organizations')
def manageable_orgs(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    stmt=select(Organization).where(Organization.is_active==True)
    if not p.is_platform_admin: stmt=stmt.where(Organization.id.in_(admin_org_ids(db,p)))
    return [{'id':str(o.id),'name':o.name} for o in db.scalars(stmt.order_by(Organization.name)).all()]

@router.get('/access/people')
def scoped_people(q:str|None=None,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    stmt=select(Person)
    if not p.is_platform_admin:
        ids=admin_org_ids(db,p)
        if not ids: raise HTTPException(403,'Organization Administrator access required')
        stmt=stmt.join(OrganizationMembership,OrganizationMembership.person_id==Person.id).where(OrganizationMembership.organization_id.in_(ids)).distinct()
    if q and q.strip():
        term=f"%{q.strip().lower()}%"; stmt=stmt.where(func.lower(Person.first_name+' '+Person.last_name).like(term))
    return [scoped_person_out(db,x,p) for x in db.scalars(stmt.order_by(Person.last_name,Person.first_name)).all()]

@router.get('/access/people/{pid}')
def scoped_person(pid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    x=db.get(Person,pid)
    if not x: raise HTTPException(404,'Person not found')
    if not p.is_platform_admin:
        visible=db.scalar(select(OrganizationMembership.id).where(OrganizationMembership.person_id==pid,OrganizationMembership.organization_id.in_(admin_org_ids(db,p))))
        if not visible: raise HTTPException(404,'Person not found')
    return scoped_person_out(db,x,p)

@router.post('/access/people',status_code=201)
def scoped_add_person(b:ScopedPersonIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    require_org(db,p,b.organization_id); norm=b.email.strip().lower(); x=db.scalar(select(Person).where(Person.normalized_email==norm))
    created=False
    if not x:
        x=Person(email=b.email.strip(),normalized_email=norm,first_name=b.first_name.strip(),last_name=b.last_name.strip(),phone=b.phone if p.is_platform_admin else None,is_active=True);db.add(x);db.flush();created=True
    m=db.scalar(select(OrganizationMembership).where(OrganizationMembership.person_id==x.id,OrganizationMembership.organization_id==b.organization_id))
    if not m: m=OrganizationMembership(person_id=x.id,organization_id=b.organization_id,is_active=True);db.add(m);db.flush()
    else:m.is_active=True
    role=db.scalar(select(Role).where(Role.key==b.role_key));
    if not role: raise HTTPException(400,'Unknown organization role')
    db.execute(delete(MembershipRole).where(MembershipRole.membership_id==m.id));db.add(MembershipRole(membership_id=m.id,role_id=role.id))
    c=db.scalar(select(PersonOrganizationContact).where(PersonOrganizationContact.person_id==x.id,PersonOrganizationContact.organization_id==b.organization_id))
    if not c: c=PersonOrganizationContact(person_id=x.id,organization_id=b.organization_id,email=b.email.strip(),phone=b.phone,supplied_by_person_id=p.id);db.add(c)
    else:c.email=b.email.strip();c.phone=b.phone;c.supplied_by_person_id=p.id
    org=db.get(Organization,b.organization_id);log(db,p,'person.organization.add','organization_membership',m.id,b.organization_id,f'Added {x.first_name} {x.last_name} to {org.name} as {role.name}.',{'matched_existing_person':not created});db.commit();return scoped_person_out(db,x,p)

@router.put('/access/people/{pid}/memberships/{oid}')
def scoped_membership(pid:UUID,oid:UUID,b:MembershipPatch,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    require_org(db,p,oid);m=db.scalar(select(OrganizationMembership).where(OrganizationMembership.person_id==pid,OrganizationMembership.organization_id==oid));x=db.get(Person,pid);org=db.get(Organization,oid)
    if not m or not x:raise HTTPException(404,'Membership not found')
    old=list(db.scalars(select(Role.name).join(MembershipRole,MembershipRole.role_id==Role.id).where(MembershipRole.membership_id==m.id)).all());m.is_active=b.is_active
    new=old
    if b.role_key:
        role=db.scalar(select(Role).where(Role.key==b.role_key));
        if not role:raise HTTPException(400,'Unknown organization role')
        db.execute(delete(MembershipRole).where(MembershipRole.membership_id==m.id));db.add(MembershipRole(membership_id=m.id,role_id=role.id));new=[role.name]
    log(db,p,'membership.update','organization_membership',m.id,oid,f'Updated {x.first_name} {x.last_name} at {org.name}: role {", ".join(old) or "Member"} → {", ".join(new) or "Member"}; status {"Active" if m.is_active else "Disabled"}.');db.commit();return scoped_person_out(db,x,p)

@router.put('/access/people/{pid}/platform-role')
def platform_role(pid:UUID,b:PlatformRolePatch,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    x=db.get(Person,pid)
    if not x:raise HTTPException(404,'Person not found')
    x.is_platform_admin=b.is_platform_admin;log(db,p,'platform.role.update','person',x.id,None,f'{"Granted Platform Administrator to" if b.is_platform_admin else "Removed Platform Administrator from"} {x.first_name} {x.last_name}.');db.commit();return scoped_person_out(db,x,p)

@router.get('/consent/status')
def consent_status(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    t=db.scalar(select(ConsentTemplate).where(ConsentTemplate.organization_id==None,ConsentTemplate.is_active==True).order_by(ConsentTemplate.version.desc()))
    if not t:return {'required':False}
    r=db.scalar(select(ConsentRecord).where(ConsentRecord.person_id==p.id,ConsentRecord.template_id==t.id,ConsentRecord.status=='signed'))
    return {'required':r is None,'template':{'id':str(t.id),'name':t.name,'version':t.version,'body':t.body},'birth_month':p.birth_month,'birth_year':p.birth_year}
class SelfConsentIn(BaseModel):
    birth_month:int=Field(ge=1,le=12);birth_year:int=Field(ge=1900,le=2100);template_id:UUID;agree:bool
@router.post('/consent/accept')
def accept_consent(b:SelfConsentIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not b.agree:raise HTTPException(400,'Consent is required to continue')
    t=db.get(ConsentTemplate,b.template_id)
    if not t or not t.is_active or t.organization_id is not None:raise HTTPException(400,'Consent version is not active')
    p.birth_month=b.birth_month;p.birth_year=b.birth_year
    now=datetime.now(timezone.utc); definitely_adult=(b.birth_year < now.year-18) or (b.birth_year == now.year-18 and b.birth_month < now.month)
    if not definitely_adult:return {'ok':False,'guardian_required':True,'message':'Guardian consent is required before access can continue.'}
    existing=db.scalar(select(ConsentRecord).where(ConsentRecord.person_id==p.id,ConsentRecord.template_id==t.id,ConsentRecord.status=='signed'))
    if not existing:db.add(ConsentRecord(session_id=None,person_id=p.id,template_id=t.id,signer_type='self',signer_name=f'{p.first_name} {p.last_name}',signer_email=p.email,status='signed'))
    log(db,p,'consent.accept','consent_record',existing.id if existing else p.id,None,f'{p.first_name} {p.last_name} accepted {t.name} version {t.version}.');db.commit();return {'ok':True,'guardian_required':False}

class GuardianConsentIn(BaseModel):
    person_id:UUID;template_id:UUID;signer_name:str;signer_email:str
@router.post('/consent/guardian',status_code=201)
def guardian_consent(b:GuardianConsentIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    target=db.get(Person,b.person_id);t=db.get(ConsentTemplate,b.template_id)
    if not target or not t or not t.is_active:raise HTTPException(404,'Person or consent version not found')
    x=ConsentRecord(session_id=None,person_id=target.id,template_id=t.id,signer_type='guardian',signer_name=b.signer_name.strip(),signer_email=b.signer_email.strip(),status='signed');db.add(x);db.flush();log(db,p,'consent.guardian','consent_record',x.id,None,f'Recorded guardian consent for {target.first_name} {target.last_name} — {t.name} version {t.version}.');db.commit();return {'id':str(x.id),'ok':True}

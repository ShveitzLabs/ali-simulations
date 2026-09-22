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
    simulation_type_id:UUID; name:str=Field(min_length=2,max_length=200); description:str|None=None; default_role_key:str|None='team_member'; role_assignment_mode:str='manual_default'; max_teams:int=Field(default=4,ge=1,le=4); status:str='available'
def template_out(x): return {'id':str(x.id),'simulation_type_id':str(x.simulation_type_id),'name':x.name,'description':x.description,'default_role_key':x.default_role_key,'role_assignment_mode':x.role_assignment_mode,'max_teams':x.max_teams,'status':x.status,'version':x.version,'archived_at':x.archived_at}
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
    x=ProgramTemplate(**b.model_dump());db.add(x);db.flush();log(db,p,'template.create','program_template',x.id,None,f'Created template “{x.name}”.');db.commit();return template_out(x)
@router.put('/templates/{tid}')
def template_update(tid:UUID,b:TemplateIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
    if not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    x=db.get(ProgramTemplate,tid)
    if not x:raise HTTPException(404,'Template not found')
    before=x.name
    for k,v in b.model_dump().items():setattr(x,k,v)
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
    if b.organization_id:require_org(db,p,b.organization_id)
    elif not p.is_platform_admin:raise HTTPException(403,'Platform administrator access required')
    x=ConsentTemplate(**b.model_dump());db.add(x);db.flush();log(db,p,'consent.template.create','consent_template',x.id,b.organization_id,f'Created consent template “{x.name}” version 1.');db.commit();return {'id':str(x.id)}
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
        xs=db.scalars(select(Person).join(OrganizationMembership,OrganizationMembership.person_id==Person.id).where(OrganizationMembership.organization_id.in_(admin_orgs),OrganizationMembership.is_active==True,Person.is_active==True).distinct().order_by(Person.last_name,Person.first_name)).all()
    return [{'id':str(x.id),'first_name':x.first_name,'last_name':x.last_name,'email':x.email} for x in xs]

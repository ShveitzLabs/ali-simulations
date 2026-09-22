import json
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import Person,OrganizationMembership,MembershipRole,Role,Session as ProgramSession,SessionTeam,SessionParticipant,ProgramTemplate,AuditEvent,SessionPartnerNeed,SessionContribution,SessionOutreach,SessionActivity,SessionHandoff
router=APIRouter(prefix='/api/session-workspace',tags=['session-workspace'])

def admin_orgs(db,p):
 rows=db.execute(select(OrganizationMembership,Role).join(MembershipRole,MembershipRole.membership_id==OrganizationMembership.id).join(Role,Role.id==MembershipRole.role_id).where(OrganizationMembership.person_id==p.id,OrganizationMembership.is_active==True)).all()
 return {m.organization_id for m,r in rows if r.key=='organization_admin'}
def access(db,p,sid):
 s=db.get(ProgramSession,sid)
 if not s:raise HTTPException(404,'Session not found')
 sp=db.scalar(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==p.id,SessionParticipant.is_active==True))
 is_admin=p.is_platform_admin or s.organization_id in admin_orgs(db,p)
 if not is_admin and not sp:raise HTTPException(403,'You are not assigned to this session')
 return s,sp,is_admin
def ensure_writable(s,p):
 if s.status in ('closed','completed','archived') and not p.is_platform_admin: raise HTTPException(403,'Closed sessions are read-only')
def team_scope(stmt,sp,is_admin,col):
 return stmt if is_admin else stmt.where(col==sp.team_id)
def audit(db,p,s,action,etype,eid,summary):db.add(AuditEvent(organization_id=s.organization_id,actor_person_id=p.id,action=action,entity_type=etype,entity_id=str(eid),detail_json=json.dumps({'summary':summary})))
def person_name(db,pid):
 p=db.get(Person,pid);return f'{p.first_name} {p.last_name}' if p else 'Unknown'
def config(t):
 try:return json.loads(t.configuration_json or '{}')
 except:return {}

@router.get('/mine')
def mine(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 
 if p.is_platform_admin:
  stmt=select(ProgramSession)
 else:
  ao=admin_orgs(db,p)
  participant_ids=select(SessionParticipant.session_id).where(SessionParticipant.person_id==p.id,SessionParticipant.is_active==True)
  stmt=select(ProgramSession).where((ProgramSession.id.in_(participant_ids)) | (ProgramSession.organization_id.in_(ao)))
 xs=db.scalars(stmt.distinct().order_by(ProgramSession.starts_at.desc().nullslast(),ProgramSession.name)).all()
 return [{'id':str(s.id),'name':s.name,'status':s.status} for s in xs]

@router.get('/{sid}')
def workspace(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,is_admin=access(db,p,sid);t=db.get(ProgramTemplate,s.template_id) if s.template_id else None;teams=db.scalars(select(SessionTeam).where(SessionTeam.session_id==sid).order_by(SessionTeam.sort_order)).all();parts=db.execute(select(SessionParticipant,Person).join(Person,Person.id==SessionParticipant.person_id).where(SessionParticipant.session_id==sid,SessionParticipant.is_active==True)).all()
 c=config(t) if t else {}; cats=c.get('collection_categories',c.get('categories',[]));
 if cats and isinstance(cats[0] if cats else None,str):cats=[{'key':x,'name':x.replace('_',' ').title()} for x in cats]
 return {'id':str(s.id),'name':s.name,'status':s.status,'starts_at':s.starts_at,'ends_at':s.ends_at,'is_admin':is_admin,'my_team_id':str(sp.team_id) if sp and sp.team_id else None,'my_role':sp.current_role_key if sp else ('administrator' if is_admin else None),'categories':cats,'teams':[{'id':str(x.id),'name':x.name} for x in teams],'participants':[{'person_id':str(x.person_id),'name':f'{who.first_name} {who.last_name}','team_id':str(x.team_id) if x.team_id else None,'role':x.current_role_key} for x,who in parts]}

class NeedIn(BaseModel):partner_name:str;category_key:str|None=None;description:str;priority:str='normal';target_quantity:float|None=None;unit:str|None=None;source_notes:str|None=None
@router.get('/{sid}/needs')
def needs(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);stmt=team_scope(select(SessionPartnerNeed).where(SessionPartnerNeed.session_id==sid),sp,a,SessionPartnerNeed.team_id);xs=db.scalars(stmt.order_by(SessionPartnerNeed.created_at.desc())).all();return [{'id':str(x.id),'team_id':str(x.team_id) if x.team_id else None,'partner_name':x.partner_name,'category_key':x.category_key,'description':x.description,'priority':x.priority,'target_quantity':x.target_quantity,'unit':x.unit,'status':x.status,'source_notes':x.source_notes,'entered_by':person_name(db,x.entered_by_person_id)} for x in xs]
@router.post('/{sid}/needs',status_code=201)
def need_add(sid:UUID,b:NeedIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);ensure_writable(s,p);x=SessionPartnerNeed(session_id=sid,team_id=sp.team_id if sp else None,entered_by_person_id=p.id,**b.model_dump());db.add(x);db.flush();audit(db,p,s,'partner_need.create','session_partner_need',x.id,f'{p.first_name} {p.last_name} reported a partner need for {x.partner_name} in “{s.name}”.');db.commit();return {'id':str(x.id)}
 ensure_writable(s,p)
@router.post('/{sid}/needs/{nid}/verify')
def need_verify(sid:UUID,nid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid)
 ensure_writable(s,p)
 if not a:raise HTTPException(403,'Administrator verification required')
 x=db.get(SessionPartnerNeed,nid)
 if not x or x.session_id!=sid:raise HTTPException(404,'Need not found')
 x.status='verified';x.verified_by_person_id=p.id;audit(db,p,s,'partner_need.verify','session_partner_need',x.id,f'{p.first_name} {p.last_name} verified a partner need for {x.partner_name} in “{s.name}”.');db.commit();return {'ok':True}

class ContributionIn(BaseModel):category_key:str|None=None;contribution_type:str;donor_name:str|None=None;quantity:float|None=None;unit:str|None=None;weight_lbs:float|None=None;amount:float|None=None;designation:str|None=None;notes:str|None=None
@router.get('/{sid}/contributions')
def contributions(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);stmt=team_scope(select(SessionContribution).where(SessionContribution.session_id==sid),sp,a,SessionContribution.team_id);xs=db.scalars(stmt.order_by(SessionContribution.created_at.desc())).all();return [{'id':str(x.id),'team_id':str(x.team_id) if x.team_id else None,'category_key':x.category_key,'contribution_type':x.contribution_type,'donor_name':x.donor_name,'quantity':x.quantity,'unit':x.unit,'weight_lbs':x.weight_lbs,'amount':x.amount,'designation':x.designation,'notes':x.notes,'qc_status':x.qc_status,'entered_by':person_name(db,x.entered_by_person_id),'created_at':x.created_at} for x in xs]
@router.post('/{sid}/contributions',status_code=201)
def contribution_add(sid:UUID,b:ContributionIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid)
 ensure_writable(s,p)
 if b.contribution_type not in ('in_kind','monetary'):raise HTTPException(400,'Contribution must be in_kind or monetary')
 if b.contribution_type=='monetary' and (b.amount is None or b.amount<0):raise HTTPException(400,'Enter a valid donation amount')
 x=SessionContribution(session_id=sid,team_id=sp.team_id if sp else None,entered_by_person_id=p.id,**b.model_dump());db.add(x);db.flush();audit(db,p,s,'contribution.create','session_contribution',x.id,f'{p.first_name} {p.last_name} logged a {b.contribution_type.replace("_"," ")} contribution in “{s.name}”.');db.commit();return {'id':str(x.id)}
@router.post('/{sid}/contributions/{cid}/verify')
def contribution_verify(sid:UUID,cid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);x=db.get(SessionContribution,cid)
 ensure_writable(s,p)
 qc=sp and sp.current_role_key=='quality_control'
 if not a and not qc:raise HTTPException(403,'Quality Control or administrator access required')
 if not x or x.session_id!=sid or (not a and x.team_id!=sp.team_id):raise HTTPException(404,'Contribution not found')
 x.qc_status='verified';x.verified_by_person_id=p.id;audit(db,p,s,'contribution.verify','session_contribution',x.id,f'{p.first_name} {p.last_name} verified a contribution in “{s.name}”.');db.commit();return {'ok':True}

class OutreachIn(BaseModel):contact_name:str|None=None;organization_name:str|None=None;method:str='other';outcome:str|None=None;follow_up_at:datetime|None=None;notes:str|None=None
@router.get('/{sid}/outreach')
def outreach(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);stmt=team_scope(select(SessionOutreach).where(SessionOutreach.session_id==sid),sp,a,SessionOutreach.team_id);xs=db.scalars(stmt.order_by(SessionOutreach.occurred_at.desc())).all();return [{'id':str(x.id),'team_id':str(x.team_id) if x.team_id else None,'contact_name':x.contact_name,'organization_name':x.organization_name,'method':x.method,'outcome':x.outcome,'follow_up_at':x.follow_up_at,'notes':x.notes,'entered_by':person_name(db,x.entered_by_person_id),'occurred_at':x.occurred_at} for x in xs]
@router.post('/{sid}/outreach',status_code=201)
def outreach_add(sid:UUID,b:OutreachIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);ensure_writable(s,p);x=SessionOutreach(session_id=sid,team_id=sp.team_id if sp else None,entered_by_person_id=p.id,**b.model_dump());db.add(x);db.flush();audit(db,p,s,'outreach.create','session_outreach',x.id,f'{p.first_name} {p.last_name} logged outreach to {x.organization_name or x.contact_name or "a contact"} in “{s.name}”.');db.commit();return {'id':str(x.id)}
 ensure_writable(s,p)

class ActivityIn(BaseModel):activity_type:str;title:str;description:str|None=None;quantity:float|None=None
@router.get('/{sid}/activities')
def activities(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);stmt=team_scope(select(SessionActivity).where(SessionActivity.session_id==sid),sp,a,SessionActivity.team_id);xs=db.scalars(stmt.order_by(SessionActivity.occurred_at.desc())).all();return [{'id':str(x.id),'team_id':str(x.team_id) if x.team_id else None,'activity_type':x.activity_type,'title':x.title,'description':x.description,'quantity':x.quantity,'entered_by':person_name(db,x.entered_by_person_id),'occurred_at':x.occurred_at} for x in xs]
@router.post('/{sid}/activities',status_code=201)
def activity_add(sid:UUID,b:ActivityIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);ensure_writable(s,p);x=SessionActivity(session_id=sid,team_id=sp.team_id if sp else None,entered_by_person_id=p.id,**b.model_dump());db.add(x);db.flush();audit(db,p,s,'activity.create','session_activity',x.id,f'{p.first_name} {p.last_name} logged “{x.title}” in “{s.name}”.');db.commit();return {'id':str(x.id)}
 ensure_writable(s,p)

class HandoffIn(BaseModel):partner_name:str;team_id:UUID|None=None;delivered_at:datetime|None=None;summary:str;impact_notes:str|None=None
@router.get('/{sid}/handoffs')
def handoffs(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);stmt=select(SessionHandoff).where(SessionHandoff.session_id==sid);stmt=stmt if a else stmt.where(SessionHandoff.team_id==sp.team_id);xs=db.scalars(stmt.order_by(SessionHandoff.created_at.desc())).all();return [{'id':str(x.id),'team_id':str(x.team_id) if x.team_id else None,'partner_name':x.partner_name,'delivered_at':x.delivered_at,'summary':x.summary,'impact_notes':x.impact_notes,'entered_by':person_name(db,x.entered_by_person_id)} for x in xs]
@router.post('/{sid}/handoffs',status_code=201)
def handoff_add(sid:UUID,b:HandoffIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid)
 ensure_writable(s,p)
 if not a:raise HTTPException(403,'Administrator access required for final handoff')
 
 if b.team_id is not None:
  team=db.get(SessionTeam,b.team_id)
  if not team or team.session_id!=sid:raise HTTPException(400,'Handoff team is not part of this session')
 x=SessionHandoff(session_id=sid,entered_by_person_id=p.id,**b.model_dump());db.add(x);db.flush();audit(db,p,s,'handoff.create','session_handoff',x.id,f'{p.first_name} {p.last_name} recorded a handoff to {x.partner_name} in “{s.name}”.');db.commit();return {'id':str(x.id)}

@router.get('/{sid}/dashboard')
def dashboard(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);team_id=None if a else sp.team_id
 def filt(model):
  stmt=select(model).where(model.session_id==sid)
  return stmt if a else stmt.where(model.team_id==team_id)
 cs=db.scalars(filt(SessionContribution)).all();os=db.scalars(filt(SessionOutreach)).all();ns=db.scalars(filt(SessionPartnerNeed)).all();acts=db.scalars(filt(SessionActivity)).all()
 by_team={}
 if a:
  teams=db.scalars(select(SessionTeam).where(SessionTeam.session_id==sid)).all()
  for t in teams:
   tc=[x for x in cs if x.team_id==t.id];by_team[str(t.id)]={'name':t.name,'contributions':len(tc),'items':sum(x.quantity or 0 for x in tc if x.contribution_type=='in_kind'),'donations':sum(x.amount or 0 for x in tc if x.contribution_type=='monetary'),'outreach':sum(1 for x in os if x.team_id==t.id)}
 return {'scope':'session' if a else 'team','contributions':len(cs),'items':sum(x.quantity or 0 for x in cs if x.contribution_type=='in_kind'),'weight_lbs':sum(x.weight_lbs or 0 for x in cs),'donations':sum(x.amount or 0 for x in cs if x.contribution_type=='monetary'),'outreach':len(os),'activities':len(acts),'reported_needs':len(ns),'verified_needs':sum(1 for x in ns if x.status=='verified'),'pending_qc':sum(1 for x in cs if x.qc_status!='verified'),'by_team':by_team}

@router.get('/{sid}/feed')
def session_feed(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=access(db,p,sid);events=[]
 teams={x.id:x.name for x in db.scalars(select(SessionTeam).where(SessionTeam.session_id==sid)).all()}
 def add(kind,x,title,detail,when,team_id=None):
  events.append({'id':f'{kind}:{x.id}','type':kind,'title':title,'detail':detail,'at':when,'team_id':str(team_id) if team_id else None,'team_name':teams.get(team_id) if team_id else None,'entered_by':person_name(db,x.entered_by_person_id)})
 for x in db.scalars(select(SessionPartnerNeed).where(SessionPartnerNeed.session_id==sid)).all():add('partner_need',x,f'Partner need reported: {x.partner_name}',x.description,x.created_at,x.team_id)
 for x in db.scalars(select(SessionContribution).where(SessionContribution.session_id==sid)).all():
  detail=f'${x.amount:,.2f}' if x.contribution_type=='monetary' and x.amount is not None else f'{x.quantity:g} {x.unit or "items"}' if x.quantity is not None else x.contribution_type.replace('_',' ')
  add('contribution',x,f'Contribution logged{f" from {x.donor_name}" if x.donor_name else ""}',detail,x.created_at,x.team_id)
 for x in db.scalars(select(SessionOutreach).where(SessionOutreach.session_id==sid)).all():add('outreach',x,f'Outreach: {x.organization_name or x.contact_name or "Community contact"}',x.outcome or x.notes or x.method,x.occurred_at,x.team_id)
 for x in db.scalars(select(SessionActivity).where(SessionActivity.session_id==sid)).all():add('activity',x,x.title,x.description or x.activity_type.replace('_',' '),x.occurred_at,x.team_id)
 # Handoffs are intentionally private to administrators and the assigned team.
 hs=select(SessionHandoff).where(SessionHandoff.session_id==sid)
 if not a:hs=hs.where(SessionHandoff.team_id==sp.team_id)
 for x in db.scalars(hs).all():add('handoff',x,f'Handoff: {x.partner_name}',x.summary,x.created_at,x.team_id)
 events.sort(key=lambda z:z['at'] or datetime.min,reverse=True)
 return events[:100]

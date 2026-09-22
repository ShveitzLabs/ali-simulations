import json
from datetime import datetime,timezone
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.dependencies import get_current_person
from ..models.core import Person,Session as ProgramSession,SessionParticipant,OrganizationMembership,MembershipRole,Role,LeadershipEvaluation,LeadershipObservation,AuditEvent
router=APIRouter(prefix='/api/leadership',tags=['leadership'])
CAPABILITIES=[('judgment_reasoning','Judgment & Reasoning'),('learning_agility','Learning Agility'),('initiative','Initiative'),('adaptability','Adaptability'),('problem_solving','Problem Solving'),('communication','Communication'),('collaboration','Collaboration'),('empathy','Empathy & Perspective-Taking'),('leadership_influence','Leadership & Influence'),('composure','Composure Under Pressure'),('accountability','Accountability & Reliability'),('self_awareness','Self-Awareness')]
def org_admin(db,p,oid):
 if p.is_platform_admin:return True
 return db.scalar(select(OrganizationMembership.id).join(MembershipRole,MembershipRole.membership_id==OrganizationMembership.id).join(Role,Role.id==MembershipRole.role_id).where(OrganizationMembership.person_id==p.id,OrganizationMembership.organization_id==oid,OrganizationMembership.is_active==True,Role.key=='organization_admin')) is not None
def session_access(db,p,sid):
 s=db.get(ProgramSession,sid)
 if not s:raise HTTPException(404,'Session not found')
 sp=db.scalar(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==p.id,SessionParticipant.is_active==True))
 admin=org_admin(db,p,s.organization_id)
 if not admin and not sp:raise HTTPException(403,'Session access required')
 return s,sp,admin
def nm(db,pid):
 x=db.get(Person,pid);return f'{x.first_name} {x.last_name}' if x else 'Unknown'
def audit(db,p,s,action,eid,summary):db.add(AuditEvent(organization_id=s.organization_id,actor_person_id=p.id,action=action,entity_type='leadership_evaluation',entity_id=str(eid),detail_json=json.dumps({'summary':summary})))
@router.get('/rubric')
def rubric():return [{'key':k,'name':n,'scale':[{'score':1,'anchor':'Rarely demonstrates the behavior; requires substantial direction.'},{'score':2,'anchor':'Demonstrates inconsistently or with frequent support.'},{'score':3,'anchor':'Demonstrates effectively in expected situations.'},{'score':4,'anchor':'Demonstrates consistently, including in challenging situations.'},{'score':5,'anchor':'Demonstrates exceptionally and positively influences others.'}]} for k,n in CAPABILITIES]
@router.get('/session/{sid}')
def session_eval(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid);parts=db.execute(select(SessionParticipant,Person).join(Person,Person.id==SessionParticipant.person_id).where(SessionParticipant.session_id==sid,SessionParticipant.is_active==True)).all()
 q=select(LeadershipEvaluation).where(LeadershipEvaluation.session_id==sid)
 if not a:q=q.where((LeadershipEvaluation.evaluator_person_id==p.id)|((LeadershipEvaluation.participant_person_id==p.id)&(LeadershipEvaluation.status=='released')))
 es=db.scalars(q.order_by(LeadershipEvaluation.created_at.desc())).all()
 return {'session':{'id':str(s.id),'name':s.name,'status':s.status},'me_id':str(p.id),'can_evaluate':a,'participants':[{'id':str(x.person_id),'name':f'{who.first_name} {who.last_name}','role':x.current_role_key} for x,who in parts],'evaluations':[{'id':str(x.id),'participant_id':str(x.participant_person_id),'participant_name':nm(db,x.participant_person_id),'evaluator_name':nm(db,x.evaluator_person_id),'context':x.context,'scores':json.loads(x.scores_json),'strength':x.strength_narrative,'growth':x.growth_narrative,'evidence':x.evidence_notes,'status':x.status,'created_at':x.created_at} for x in es]}
class EvalIn(BaseModel):participant_person_id:UUID;context:str='general';scores:dict[str,int];strength_narrative:str;growth_narrative:str;evidence_notes:str|None=None
@router.post('/session/{sid}/evaluations',status_code=201)
def add_eval(sid:UUID,b:EvalIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid)
 if not a:raise HTTPException(403,'Evaluator or administrator access required')
 if b.participant_person_id==p.id:raise HTTPException(400,'You cannot evaluate yourself')
 valid={k for k,_ in CAPABILITIES}
 if set(b.scores)!=valid or any(v<1 or v>5 for v in b.scores.values()):raise HTTPException(400,'Score all 12 leadership capabilities from 1 to 5')
 if not db.scalar(select(SessionParticipant.id).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==b.participant_person_id)):raise HTTPException(400,'Participant is not assigned to this session')
 x=LeadershipEvaluation(session_id=sid,participant_person_id=b.participant_person_id,evaluator_person_id=p.id,context=b.context,scores_json=json.dumps(b.scores),strength_narrative=b.strength_narrative,growth_narrative=b.growth_narrative,evidence_notes=b.evidence_notes);db.add(x);db.flush();audit(db,p,s,'evaluation.submit',x.id,f'{p.first_name} {p.last_name} submitted a leadership evaluation for {nm(db,b.participant_person_id)} in “{s.name}”.');db.commit();return {'id':str(x.id)}
@router.post('/session/{sid}/evaluations/{eid}/{action}')
def workflow(sid:UUID,eid:UUID,action:str,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid)
 if not a:raise HTTPException(403,'Administrator access required')
 x=db.get(LeadershipEvaluation,eid)
 if not x or x.session_id!=sid:raise HTTPException(404,'Evaluation not found')
 if x.evaluator_person_id==p.id:raise HTTPException(403,'You cannot approve, exclude, or release your own evaluation')
 now=datetime.now(timezone.utc)
 if action=='approve':x.status='approved';x.approved_by_person_id=p.id;x.approved_at=now
 elif action=='release':
  if x.status!='approved':raise HTTPException(400,'Approve the evaluation before release')
  x.status='released';x.released_by_person_id=p.id;x.released_at=now
 elif action=='exclude':x.status='excluded'
 else:raise HTTPException(400,'Unknown workflow action')
 audit(db,p,s,f'evaluation.{action}',x.id,f'{p.first_name} {p.last_name} {action}d a leadership evaluation for {nm(db,x.participant_person_id)} in “{s.name}”.');db.commit();return {'ok':True,'status':x.status}
class ObsIn(BaseModel):participant_person_id:UUID;capability_key:str;context:str='general';note:str
@router.post('/session/{sid}/observations',status_code=201)
def observation(sid:UUID,b:ObsIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid)
 if not a:raise HTTPException(403,'Leadership staff access required')
 if b.capability_key not in {k for k,_ in CAPABILITIES}:raise HTTPException(400,'Unknown capability')
 x=LeadershipObservation(session_id=sid,participant_person_id=b.participant_person_id,observer_person_id=p.id,capability_key=b.capability_key,context=b.context,note=b.note);db.add(x);db.commit();return {'id':str(x.id)}
@router.get('/journey')
def journey(db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 es=db.scalars(select(LeadershipEvaluation).where(LeadershipEvaluation.participant_person_id==p.id,LeadershipEvaluation.status=='released').order_by(LeadershipEvaluation.created_at.desc())).all()
 return [{'id':str(x.id),'session_id':str(x.session_id),'session_name':db.get(ProgramSession,x.session_id).name,'scores':json.loads(x.scores_json),'strength':x.strength_narrative,'growth':x.growth_narrative,'created_at':x.created_at} for x in es]

# v0.10.1 participant peer feedback. Repeated ratings by one evaluator are averaged
# per capability before they contribute to the recipient's aggregate, preventing
# repeated submissions by one teammate from carrying extra numeric weight.
from ..models.core import LeadershipPeerFeedback
class PeerFeedbackIn(BaseModel):
 participant_person_id:UUID
 scores:dict[str,int|None]
 note:str|None=None

@router.post('/session/{sid}/peer-feedback',status_code=201)
def peer_feedback(sid:UUID,b:PeerFeedbackIn,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid)
 if not sp:raise HTTPException(403,'Participants may provide teammate feedback')
 if s.status in ('closed','completed','archived'):raise HTTPException(403,'Closed sessions are read-only')
 if b.participant_person_id==p.id:raise HTTPException(400,'You cannot evaluate yourself')
 target=db.scalar(select(SessionParticipant).where(SessionParticipant.session_id==sid,SessionParticipant.person_id==b.participant_person_id,SessionParticipant.is_active==True))
 if not target or target.team_id!=sp.team_id:raise HTTPException(403,'Peer feedback is limited to your current teammates')
 valid={k for k,_ in CAPABILITIES}
 if not set(b.scores).issubset(valid):raise HTTPException(400,'Unknown leadership capability')
 cleaned={k:v for k,v in b.scores.items() if v is not None}
 if any(v<1 or v>5 for v in cleaned.values()):raise HTTPException(400,'Ratings must be from 1 to 5')
 if not cleaned and not (b.note or '').strip():raise HTTPException(400,'Provide at least one rating or a feedback note')
 x=LeadershipPeerFeedback(session_id=sid,participant_person_id=b.participant_person_id,evaluator_person_id=p.id,scores_json=json.dumps(cleaned),note=(b.note or '').strip() or None)
 db.add(x);db.flush();audit(db,p,s,'peer_feedback.submit',x.id,f'{p.first_name} {p.last_name} submitted teammate feedback in “{s.name}”.');db.commit();return {'id':str(x.id)}

@router.get('/session/{sid}/peer-feedback')
def peer_feedback_summary(sid:UUID,db:Session=Depends(get_db),p:Person=Depends(get_current_person)):
 s,sp,a=session_access(db,p,sid)
 # participants see who they may rate and their own submission history; admins see aggregates.
 parts=db.execute(select(SessionParticipant,Person).join(Person,Person.id==SessionParticipant.person_id).where(SessionParticipant.session_id==sid,SessionParticipant.is_active==True)).all()
 if sp: parts=[(x,w) for x,w in parts if x.team_id==sp.team_id and x.person_id!=p.id]
 xs=db.scalars(select(LeadershipPeerFeedback).where(LeadershipPeerFeedback.session_id==sid)).all()
 if not a: xs=[x for x in xs if x.evaluator_person_id==p.id]
 aggregates={}
 if a:
  allx=db.scalars(select(LeadershipPeerFeedback).where(LeadershipPeerFeedback.session_id==sid)).all()
  by_target={}
  for x in allx:by_target.setdefault(x.participant_person_id,[]).append(x)
  for pid,feedback in by_target.items():
   evaluator_means={}
   for x in feedback:
    scores=json.loads(x.scores_json or '{}')
    for k,v in scores.items():evaluator_means.setdefault((x.evaluator_person_id,k),[]).append(v)
   cap={}
   for k,_ in CAPABILITIES:
    vals=[sum(v)/len(v) for (eid,key),v in evaluator_means.items() if key==k]
    cap[k]=round(sum(vals)/len(vals),2) if vals else None
   aggregates[str(pid)]=cap
 return {'can_submit':sp is not None and s.status not in ('closed','completed','archived'),'participants':[{'id':str(x.person_id),'name':f'{who.first_name} {who.last_name}','role':x.current_role_key} for x,who in parts],'my_feedback':[{'id':str(x.id),'participant_id':str(x.participant_person_id),'scores':json.loads(x.scores_json),'note':x.note,'created_at':x.created_at} for x in xs],'aggregates':aggregates}

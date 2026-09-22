from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.core import Person, Organization, OrganizationMembership, MembershipRole, Role
from ..auth.security import verify_password, create_access_token, hash_password
from ..auth.dependencies import get_current_person

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    normalized = body.email.strip().lower()
    person = db.scalar(select(Person).where(Person.normalized_email == normalized))
    if not person or not person.password_hash or not verify_password(body.password, person.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not person.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return {"access_token": create_access_token(str(person.id)), "token_type": "bearer", "must_change_password": person.must_change_password}

@router.get("/me")
def me(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    rows=db.execute(select(OrganizationMembership,Organization).join(Organization,Organization.id==OrganizationMembership.organization_id).where(OrganizationMembership.person_id==person.id,OrganizationMembership.is_active==True)).all()
    memberships=[]
    for membership,org in rows:
        roles=list(db.scalars(select(Role.name).join(MembershipRole,MembershipRole.role_id==Role.id).where(MembershipRole.membership_id==membership.id)).all())
        memberships.append({"organization_id":str(org.id),"organization_name":org.name,"roles":roles})
    role_keys=list(db.scalars(select(Role.key).join(MembershipRole,MembershipRole.role_id==Role.id).join(OrganizationMembership,OrganizationMembership.id==MembershipRole.membership_id).where(OrganizationMembership.person_id==person.id,OrganizationMembership.is_active==True)).all())
    return {"id": str(person.id), "email": person.email, "first_name": person.first_name, "last_name": person.last_name, "is_platform_admin": person.is_platform_admin, "is_organization_admin": "organization_admin" in role_keys, "memberships":memberships}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
def change_password(body: ChangePasswordRequest, person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    if not person.password_hash or not verify_password(body.current_password, person.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if len(body.new_password) < 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 12 characters")
    if body.new_password.lower() == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a stronger password")
    person.password_hash = hash_password(body.new_password)
    person.must_change_password = False
    db.commit()
    return {"ok": True}

@router.post('/revert-impersonation')
def revert_impersonation(credentials = Depends(__import__('app.auth.dependencies',fromlist=['bearer']).bearer), db: Session=Depends(get_db)):
    from ..auth.security import decode_access_claims, create_access_token
    import uuid
    if not credentials: raise HTTPException(401,'Authentication required')
    try: claims=decode_access_claims(credentials.credentials); actor=claims.get('actor')
    except Exception: raise HTTPException(401,'Invalid token')
    if not actor: raise HTTPException(400,'Not currently viewing as another user')
    p=db.get(Person,uuid.UUID(actor))
    if not p or not p.is_active: raise HTTPException(401,'Administrator account unavailable')
    return {'access_token':create_access_token(str(p.id))}

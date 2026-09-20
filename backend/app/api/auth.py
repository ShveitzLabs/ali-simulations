from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.core import Person
from ..auth.security import verify_password, create_access_token
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
def me(person: Person = Depends(get_current_person)):
    return {"id": str(person.id), "email": person.email, "first_name": person.first_name, "last_name": person.last_name, "is_platform_admin": person.is_platform_admin}

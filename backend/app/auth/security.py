from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from ..config import settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)

def create_access_token(person_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": person_id, "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    return str(payload["sub"])

def create_impersonation_token(person_id: str, actor_person_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": person_id, "actor": actor_person_id, "impersonating": True, "iat": now, "exp": now + timedelta(minutes=min(settings.access_token_minutes, 60))}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def decode_access_claims(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db, User, SessionToken, AuditLog

ROLES = ['ADMIN', 'FRAUD_INVESTIGATOR', 'ANALYST', 'AUDITOR', 'SUPERVISOR']

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}${digest}'

def verify_password(password, stored):
    salt, digest = stored.split('$')
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, digest)

def token_digest(token): return hashlib.sha256(token.encode()).hexdigest()

def create_session(db, user, hours=8):
    token = secrets.token_urlsafe(48)
    db.add(SessionToken(token_hash=token_digest(token), user_id=user.id, expires_at=(datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()))
    db.commit()
    return token

def current_user(request: Request, db: Session = Depends(get_db)):
    auth = request.headers.get('Authorization', '')
    token = auth[7:] if auth.startswith('Bearer ') else request.cookies.get('bank_session', '')
    session = db.get(SessionToken, token_digest(token))
    if not session or datetime.fromisoformat(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, 'Authentication required')
    user = db.get(User, session.user_id)
    if not user or not user.active: raise HTTPException(401, 'Inactive user')
    return user

def roles(*allowed):
    def check(user: User = Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403, 'Insufficient role')
        return user
    return check

def audit(db, user, action, entity_id='', payload=None):
    db.add(AuditLog(user_id=user.id, action=action, entity_id=entity_id, payload=payload or {}))

def case_access(user, case):
    if user.role == 'FRAUD_INVESTIGATOR' and case.assigned_to != user.id:
        raise HTTPException(403, 'Investigation is assigned to another investigator')
    if user.role not in ['ADMIN', 'SUPERVISOR', 'FRAUD_INVESTIGATOR', 'AUDITOR']:
        raise HTTPException(403, 'Investigation access denied')

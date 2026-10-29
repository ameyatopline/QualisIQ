"""Demo authentication. Production deployments must replace PBKDF2/local passwords with SSO, MFA and validated e-signatures."""
import os, time, secrets, hashlib, hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

APP_ENV = os.getenv('APP_ENV', 'demo')
if APP_ENV not in {'demo','production'}:
    raise RuntimeError('APP_ENV must be demo or production')
DEMO_SECRET = 'LOCAL-ONLY-NEVER-USE-IN-PRODUCTION-CHANGE-ME'
JWT_SECRET = os.getenv('JWT_SECRET', DEMO_SECRET)
if APP_ENV == 'production':
    if JWT_SECRET == DEMO_SECRET or len(JWT_SECRET) < 32:
        raise RuntimeError('Production requires a unique JWT_SECRET >=32 characters')
    if not os.getenv('ALLOWED_HOSTS') or '*' in os.getenv('ALLOWED_HOSTS',''):
        raise RuntimeError('Production requires explicit ALLOWED_HOSTS')
    if not os.getenv('DATABASE_URL','').startswith(('postgresql://','postgresql+psycopg://')):
        raise RuntimeError('Production requires a configured PostgreSQL DATABASE_URL')

bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 230000)
    return 'pbkdf2_sha256$230000$' + salt.hex() + '$' + key.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        method, rounds, salt, digest = stored.split('$')
        if method != 'pbkdf2_sha256': return False
        match = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(match, bytes.fromhex(digest))
    except Exception:
        return False

def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id),'tenant_id':user.tenant_id,'role':user.role,
                       'iat':now,'exp':now+timedelta(hours=2),'iss':'qualisiq','aud':'quality-workbench','jti':secrets.token_hex(16)}, JWT_SECRET, algorithm='HS256')

def get_current_user(credentials: HTTPAuthorizationCredentials | None=Depends(bearer), db: Session=Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail='Bearer authentication required')
    try:
        claims = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'],issuer='qualisiq',audience='quality-workbench',options={'require':['exp','iat','sub','iss','aud','jti']})
        user = db.get(User, int(claims['sub']))
        if not user or not user.active or user.tenant_id != claims['tenant_id'] or user.role != claims['role']:
            raise ValueError('Invalid account')
        return user
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

def need_role(*roles):
    def checker(user: User=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail='Role not authorized')
        return user
    return checker

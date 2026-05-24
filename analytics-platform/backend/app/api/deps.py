import secrets
import hashlib
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
import redis.asyncio as aioredis
from app.core.config import settings
from app.db.session import get_db
from app.models.schemas import User, APIKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Shared Redis connector instance for rate limiting cache lookup
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

def generate_secure_api_key() -> tuple[str, str, str]:
    raw_key = f"sk_live_{secrets.token_hex(24)}"
    prefix = raw_key[:12]
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, prefix, hashed_key

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate active session credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

async def verify_api_key_and_get_org(api_key: str = Depends(api_key_header), db: AsyncSession = Depends(get_db)) -> int:
    """Extracts and validates X-API-Key tokens to return the associated organization bound context"""
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Access Token Header (X-API-Key)")
    
    hashed_incoming = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(select(APIKey).where(APIKey.hashed_key == hashed_incoming, APIKey.is_active == True))
    key_record = result.scalar_one_or_none()
    
    if not key_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked security access credentials")
        
    return key_record.org_id

async def apply_rate_limit(org_id: int = Depends(verify_api_key_and_get_org)):
    """Implements a rolling window rate limiter via Redis cluster keys to satisfy spec metrics limits"""
    current_time = int(datetime.utcnow().timestamp())
    redis_key = f"rate_limit:{org_id}:{current_time // 60}" # 1-minute window block partitions
    
    # Allow 1000 ingestion transactions per minute per tenant org boundary context
    request_count = await redis_client.incr(redis_key)
    if request_count == 1:
        await redis_client.expire(redis_key, 59)
        
    if request_count > 1000:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Tenant data ingestion burst limits breached. Backoff requested.")

def require_roles(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Deficient organization security privileges.")
        return current_user
    return role_checker
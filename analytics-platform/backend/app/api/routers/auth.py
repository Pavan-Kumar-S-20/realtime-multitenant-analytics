from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings
from app.db.session import get_db
from app.models.schemas import User, Organization, UserSignUp, UserLogin, Token
from app.api.deps import get_password_hash, verify_password

router = APIRouter()

def create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta
    return jwt.encode({"exp": expire, "sub": str(user_id), "type": token_type}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignUp, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Account with email already registered.")
    
    # Atomic initialization of Multi-Tenant Org boundaries [cite: 11, 46]
    org = Organization(name=payload.org_name)
    db.add(org)
    await db.flush() 
    
    user = User(email=payload.email, hashed_password=get_password_hash(payload.password), org_id=org.id, role="Owner")
    db.add(user)
    await db.commit()
    return {"status": "success", "message": "Tenant framework and Owner administrative account instantiated."}

@router.post("/login", response_model=Token)
async def login(payload: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credential parameters provided.")
    
    access = create_token(user.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh = create_token(user.id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    
    # Store long-lived session pointer into HTTP-Only storage matrix [cite: 10, 46]
    response.set_cookie(key="refresh_token", value=refresh, httponly=True, secure=True, samesite="lax")
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
"""
FastAPI router: Authentication endpoints (register, login, anonymous).
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db, User
from api.schemas import UserRegister, UserLogin, TokenResponse
from api.auth import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from api.core.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    # Check uniqueness
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_anonymous=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    logger.info(f"User registered: {user.username} (ID: {user.id})")
    return TokenResponse(access_token=token, username=user.username, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    token = create_access_token({"sub": str(user.id)})
    logger.info(f"User logged in: {user.username} (ID: {user.id})")
    return TokenResponse(access_token=token, username=user.username, user_id=user.id)


@router.post("/anonymous", response_model=TokenResponse, status_code=201)
def anonymous_login(db: Session = Depends(get_db)):
    """Create a temporary anonymous user for no-login chat access."""
    anon_id = uuid.uuid4().hex[:10]
    user = User(
        username=f"anon_{anon_id}",
        email=None,
        hashed_password=get_password_hash(uuid.uuid4().hex),
        is_anonymous=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    logger.info(f"Anonymous user created: {user.username}")
    return TokenResponse(access_token=token, username=user.username, user_id=user.id)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_anonymous": current_user.is_anonymous,
    }

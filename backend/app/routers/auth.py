"""Authentication and user-management endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import (
    CurrentUser, create_access_token, hash_password, require_admin, verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import Token, UserCreate, UserOut
from ..services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    audit.log(db, user.id, "login")
    token = create_access_token(user.email, user.role)
    return Token(access_token=token, role=user.role, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/users", response_model=UserOut, dependencies=[Depends(require_admin)])
def create_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.role not in ("admin", "hr"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = User(
        email=payload.email, full_name=payload.full_name, role=payload.role,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

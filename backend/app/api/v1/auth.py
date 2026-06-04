"""Auth endpoints: register, login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditEvent
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import audit_service, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        tokens, user = await auth_service.register(
            db,
            organization_name=body.organization_name,
            email=body.email,
            password=body.password,
        )
    except auth_service.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await audit_service.record(
        db,
        event=AuditEvent.login_success,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        meta={"via": "register"},
        commit=True,
    )
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        tokens, user = await auth_service.authenticate(
            db, email=body.email, password=body.password
        )
    except auth_service.AuthError as exc:
        await audit_service.record(
            db,
            event=AuditEvent.login_failed,
            meta={"email": body.email},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc

    await audit_service.record(
        db,
        event=AuditEvent.login_success,
        organization_id=user.organization_id,
        actor_user_id=user.id,
        commit=True,
    )
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await auth_service.refresh(db, refresh_token=body.refresh_token)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user

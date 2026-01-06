from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from base_requests import RegisterRequest, LoginRequest, TokenResponse, ChangePasswordRequest, UpdateMeRequest, MeResponse
from impl.config import settings
from impl.db.session import SessionLocal
from impl.db.models import User
from impl.security.passwords import hash_password, verify_password
from impl.security.jwt import create_access_token


class AuthService:
    def _issue_token(self, *, user: User) -> TokenResponse:
        token, exp = create_access_token(
            subject=str(user.id),
            claims={"uid": user.id, "email": user.email},
            expires_minutes=settings.jwt_access_token_expire_minutes,
        )
        return TokenResponse(access_token=token, expires_in_seconds=exp)

    def register(self, req: RegisterRequest) -> TokenResponse:
        with SessionLocal() as db:
            existing = db.query(User).filter(User.email == req.email).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

            user = User(email=req.email, password_hash=hash_password(req.password))
            db.add(user)
            db.commit()
            db.refresh(user)
            return self._issue_token(user=user)

    def login(self, req: LoginRequest) -> TokenResponse:
        with SessionLocal() as db:
            user = self._authenticate(db, email=req.email, password=req.password)
            return self._issue_token(user=user)

    def login_password(self, *, email: str, password: str) -> TokenResponse:
        with SessionLocal() as db:
            user = self._authenticate(db, email=email, password=password)
            return self._issue_token(user=user)

    def _authenticate(self, db: Session, *, email: str, password: str) -> User:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    def change_password(self, *, user_id: int, req: ChangePasswordRequest) -> None:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            if not verify_password(req.current_password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
            user.password_hash = hash_password(req.new_password)
            db.commit()

    def update_me(self, *, user_id: int, req: UpdateMeRequest) -> MeResponse:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            if req.email and req.email != user.email:
                exists = db.query(User).filter(User.email == req.email).first()
                if exists:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
                user.email = req.email

            db.commit()
            db.refresh(user)
            return MeResponse(id=user.id, email=user.email, created_at=user.created_at.isoformat())

import re
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain a letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a digit")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department: str | None
    location: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


def error_response(status_code: int, code: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post("/register", status_code=201, response_model=UserOut)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    settings = get_settings()
    allowed_domains = settings.allowed_email_domain_list

    if not allowed_domains:
        return error_response(
            503,
            "REGISTRATION_NOT_CONFIGURED",
            "Registration is temporarily unavailable.",
        )

    domain = payload.email.rsplit("@", 1)[1]
    if domain not in allowed_domains:
        return error_response(
            400,
            "INVALID_EMAIL_DOMAIN",
            "Email domain is not approved for registration.",
        )

    existing = db.scalar(select(User).where(User.email == payload.email))

    if existing:
        return error_response(
            409,
            "EMAIL_EXISTS",
            "An account with this email already exists.",
        )

    password_hash = bcrypt.hashpw(
        payload.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=password_hash,
        role="student",
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        return error_response(
            409,
            "EMAIL_EXISTS",
            "An account with this email already exists.",
        )

    return user


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    settings = get_settings()

    user = db.scalar(select(User).where(User.email == payload.email))

    # Return the same error for an unknown email and wrong password.
    if user is None or not user.active:
        return error_response(
            401,
            "INVALID_CREDENTIALS",
            "Invalid email or password.",
        )

    try:
        password_matches = bcrypt.checkpw(
            payload.password.encode("utf-8"),
            user.password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        password_matches = False

    if not password_matches:
        return error_response(
            401,
            "INVALID_CREDENTIALS",
            "Invalid email or password.",
        )

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)

    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "exp": expires_at,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )

import re
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.login_rate_limit import LoginRateLimiter
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)


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
    expiresIn: int
    user: UserOut

    model_config = ConfigDict(populate_by_name=True)


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
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
):
    settings = get_settings()
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    # Block the next attempt once five failures remain in the window.
    retry_after = login_rate_limiter.retry_after(email, client_ip)
    if retry_after is not None:
        response = error_response(
            429,
            "LOGIN_RATE_LIMITED",
            "Too many failed login attempts. Try again later.",
        )
        response.headers["Retry-After"] = str(retry_after)
        return response

    user = db.scalar(select(User).where(User.email == email))

    # Keep unknown emails and incorrect passwords indistinguishable.
    if user is None or not user.active:
        login_rate_limiter.record_failure(email, client_ip)
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
        login_rate_limiter.record_failure(email, client_ip)
        return error_response(
            401,
            "INVALID_CREDENTIALS",
            "Invalid email or password.",
        )

    # A successful login clears this email/IP pair's previous failures.
    login_rate_limiter.record_success(email, client_ip)

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)

    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "ver": user.token_version,
            "exp": expires_at,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expiresIn=settings.jwt_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Validate Bearer JWT and return the authenticated active user (SR-002)."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "ver"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature or payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.scalar(select(User).where(User.id == user_id_int))
    if user is None or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_ver = payload.get("ver")
    if token_ver is None or token_ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Invalidate all existing tokens for the current user (F-003).

    Atomically increments token_version so every previously issued JWT fails the
    version check in get_current_user.
    """
    db.execute(
        update(User).where(User.id == current_user.id).values(token_version=User.token_version + 1)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

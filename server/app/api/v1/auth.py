import hashlib
import os
import secrets
from typing import Dict, Optional
from fastapi import APIRouter, Form, Request, Response, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.core.database import get_db
from server.app.database.models import User

router = APIRouter()
templates = Jinja2Templates(directory="server/app/ui/templates")

# Memory-backed secure session store: session_id -> username
SESSIONS: Dict[str, str] = {}


def hash_password(password: str) -> str:
    """Hash password securely using PBKDF2-SHA256 with a random salt."""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pw_hash.hex()


def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify standard text password against stored hash."""
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pw_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pw_hash.hex() == hash_hex
    except Exception:
        return False


def get_current_user_session(request: Request) -> Optional[str]:
    """Dependency helper to read and validate cookie session."""
    session_id = request.cookies.get("sensiwatch_session")
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    return None


@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request) -> Response:
    """Renders the admin login credential entrance."""
    # If already logged in, redirect to dashboard
    if get_current_user_session(request):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def handle_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Validates admin user and issues an HTTP-Only session cookie."""
    # 1. First, check if any user exists in SQLite. If not, auto-seed a default account!
    query = select(User)
    result = await db.execute(query)
    user_exists = result.scalar_one_or_none()

    if not user_exists:
        # Seed default administrative credentials for the MVP
        seeded_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="SuperAdmin"
        )
        db.add(seeded_user)
        await db.commit()

    # 2. Authenticate
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user.password_hash, password):
        # Return login page with error
        return templates.TemplateResponse(
            request, 
            "login.html", 
            {"error": "Invalid username or password."}
        )

    # 3. Create Session
    session_id = secrets.token_hex(16)
    SESSIONS[session_id] = username

    # 4. Redirect to Dashboard with Session Cookie
    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key="sensiwatch_session",
        value=session_id,
        httponly=True,
        samesite="lax"
    )
    return redirect


@router.get("/logout")
async def logout(request: Request) -> Response:
    """Invalidates the session and redirects to login."""
    session_id = request.cookies.get("sensiwatch_session")
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    
    response = RedirectResponse(url="/api/v1/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("sensiwatch_session")
    return response
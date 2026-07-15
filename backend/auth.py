import os
import json
import jwt
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from database import User, SessionLocal

# 🏗️ DYNAMIC PATHING
if os.environ.get("RUNNING_IN_DOCKER") == "true":
    CREDENTIALS_PATH = Path("/app/secrets/credentials.json")
    IS_PRODUCTION = True
else:
    BASE_DIR = Path(__file__).resolve().parent
    CREDENTIALS_PATH = BASE_DIR / 'secrets' / 'credentials.json'
    IS_PRODUCTION = False

# In production, ALWAYS pull this from an environment variable!
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-local-key")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ONLY FOR LOCAL DEV: Allows OAuth over HTTP instead of HTTPS
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" 

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# Create the auth router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@auth_router.get("/login")
def login_with_google():
    """Generates the Google OAuth URL and redirects the user."""
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/auth/callback'
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' 
    )
    return RedirectResponse(url=authorization_url)

@auth_router.get("/callback")
def google_auth_callback(state: str, code: str, db: Session = Depends(get_db)):
    """Handles the redirect from Google, saves tokens, and issues an HTTP-only JWT."""
    try:
        flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri='http://localhost:8000/auth/callback',
            state=state
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Load Client ID for verification
        with open(CREDENTIALS_PATH, 'r') as f:
            client_id = json.load(f)["web"]["client_id"]
            
        # Verify and extract identity
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, 
            GoogleRequest(), 
            client_id
        )
        
        user_email = id_info.get("email")
        google_id = id_info.get("sub")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Email not provided by Google.")
            
        # Update or create user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(email=user_email, google_id=google_id)
            db.add(user)
            
        user.access_token = credentials.token
        user.refresh_token = credentials.refresh_token
        user.token_expiry = credentials.expiry
        db.commit()
        
        # Generate the Session JWT
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        session_data = {"sub": user.email, "exp": expire}
        session_token = jwt.encode(session_data, SECRET_KEY, algorithm="HS256")
        
        # Bake the HTTP-Only cookie into the redirect back to React
        redirect = RedirectResponse(url=f"{FRONTEND_URL}/?login=success")
        redirect.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,  
            secure=IS_PRODUCTION,  
            samesite="none" if IS_PRODUCTION else "lax", 
            max_age=7 * 24 * 60 * 60 
        )
        return redirect
        
    except Exception as e:
        print(f"❌ OAuth Error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed.")


# --- UTILITIES ---

def get_user_credentials(user) -> Credentials:
    """Reconstructs Google Credentials from the user's DB record."""
    if not user or not user.access_token or not user.refresh_token:
        raise HTTPException(status_code=401, detail="User is not authenticated with Google.")

    try:
        with open(CREDENTIALS_PATH, 'r') as f:
            client_config = json.load(f)["web"] 
    except Exception as e:
        raise RuntimeError(f"Could not load client secrets: {e}")

    creds = Credentials(
        token=user.access_token,
        refresh_token=user.refresh_token,
        token_uri=client_config["token_uri"],
        client_id=client_config["client_id"],
        client_secret=client_config["client_secret"],
        scopes=SCOPES
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:
            raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    return creds
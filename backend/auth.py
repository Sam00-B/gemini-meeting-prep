import os
import json
import jwt
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response ,HTTPException,Request
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from database import User, SessionLocal

# 🏗️ DYNAMIC PATHING
# 1. Check for Render's default Secret File mount first
if os.path.exists("/etc/secrets/credentials.json"):
    CREDENTIALS_PATH = Path("/etc/secrets/credentials.json")
    IS_PRODUCTION = True
# 2. Fallback for standard Docker environments
elif os.environ.get("RUNNING_IN_DOCKER") == "true":
    CREDENTIALS_PATH = Path("/app/secrets/credentials.json")
    IS_PRODUCTION = True
# 3. Local development
else:
    BASE_DIR = Path(__file__).resolve().parent
    CREDENTIALS_PATH = BASE_DIR / 'secrets' / 'credentials.json'
    IS_PRODUCTION = False

# --- DYNAMIC OAUTH ROUTING ---
# In production, pull this from Render env vars. Locally, it defaults to localhost.
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# This creates the exact callback URL Google needs dynamically
REDIRECT_URI = f"{BACKEND_URL}/auth/callback"

# In production, ALWAYS pull this from an environment variable!
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-local-key")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ONLY FOR LOCAL DEV: Allows OAuth over HTTP instead of HTTPS
if not IS_PRODUCTION:
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
        redirect_uri=REDIRECT_URI # 👈 Uses dynamic URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' 
    )
    return RedirectResponse(url=authorization_url)

@auth_router.get("/login")
def login_with_google():
    """Generates the Google OAuth URL with PKCE and redirects the user."""
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=True  # 👈 1. Force PKCE generation
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' 
    )
    
    redirect = RedirectResponse(url=authorization_url)
    
    # 🍪 2. Stateless PKCE: Store the verifier and state in temporary, secure cookies
    cookie_args = {
        "httponly": True,
        "secure": IS_PRODUCTION,
        "samesite": "none" if IS_PRODUCTION else "lax",
        "max_age": 600  # 10 minutes is plenty of time to complete the login
    }
    
    redirect.set_cookie(key="oauth_state", value=state, **cookie_args)
    redirect.set_cookie(key="code_verifier", value=flow.code_verifier, **cookie_args)
    
    return redirect


@auth_router.get("/callback")
def google_auth_callback(request: Request, state: str, code: str, db: Session = Depends(get_db)):
    """Handles the redirect from Google, verifies PKCE, and issues a JWT."""
    try:
        # 1️⃣ Retrieve the PKCE verifier and state from our temporary cookies
        saved_state = request.cookies.get("oauth_state")
        code_verifier = request.cookies.get("code_verifier")
        
        if not saved_state or not code_verifier:
            raise HTTPException(status_code=400, detail="OAuth session expired or missing PKCE verifier. Please try again.")
            
        if state != saved_state:
            raise HTTPException(status_code=400, detail="CSRF Warning! State mismatch.")

        # 2️⃣ Reconstruct the flow
        flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )
        
        # 3️⃣ Inject the code verifier back into the flow for the final token exchange
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # --- Database & Identity Logic ---
        with open(CREDENTIALS_PATH, 'r') as f:
            client_id = json.load(f)["web"]["client_id"]
            
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, 
            GoogleRequest(), 
            client_id
        )
        
        user_email = id_info.get("email")
        google_id = id_info.get("sub")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Email not provided by Google.")
            
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(email=user_email, google_id=google_id)
            db.add(user)
            
        user.access_token = credentials.token
        user.refresh_token = credentials.refresh_token
        user.token_expiry = credentials.expiry
        db.commit()
        
        # --- JWT Generation ---
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        session_data = {"sub": user.email, "exp": expire}
        session_token = jwt.encode(session_data, SECRET_KEY, algorithm="HS256")
        
        redirect = RedirectResponse(url=f"{FRONTEND_URL}/?login=success")
        
        # 🧹 4. Clean up the temporary PKCE cookies
        redirect.delete_cookie("oauth_state")
        redirect.delete_cookie("code_verifier")
        
        # 🍪 5. Set the real authentication session token
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
        raise HTTPException(status_code=400, detail=f"Authentication failed. Reason: {str(e)}")

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
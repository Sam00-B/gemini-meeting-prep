import os.path
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
#  Requesting READ-ONLY access to both Calendar and Gmail. 
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]
# 🏗️ DYNAMIC PATHING: 
# __file__ is auth.py. 
# .resolve().parent is the /backend folder. 
# .parent again is the root folder.
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'
TOKEN_PATH = BASE_DIR / 'token.json'
def authenticate_google_workspace()->Credentials:
    """
    Handles OAuth2 flow for Google Workspace.
    Returns valid user credentials, utilizing cached tokens if available.
    """
    creds=None
    # token.json stores the user's access and refresh tokens.
    # It is generated automatically after the first successful login.
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    # If there are no valid credentials available, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Initiating OAuth2 flow...")
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError("Missing 'credentials.json'. Please provide your OAuth2 client credentials.")
            flow=InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            # spins up a local server to receive the auth callback
            creds=flow.run_local_server(port=0,timeout_seconds=300)
        # Save the credentials for the next run
        with open(str(TOKEN_PATH), 'w') as token:
            token.write(creds.to_json())
    return creds
if __name__ == "__main__":
    print("Testing Authentication Module...")
    credentials = authenticate_google_workspace()
    print("✅ Authentication successful! Token is ready.")
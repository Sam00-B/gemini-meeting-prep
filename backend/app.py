import os
import jwt
from dotenv import load_dotenv
import google.genai as genai
from fastapi import FastAPI, HTTPException, Depends, Cookie
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import our custom data pipelines and new auth dependencies
from calendar_service import get_today_meetings
from gmail_service import get_email_context
from database import engine, SessionLocal, Base, BriefingCache, User
from auth import get_user_credentials, auth_router, SECRET_KEY

load_dotenv() 

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=API_KEY)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Executive Assistant API")

FRONTEND_URL = os.getenv("FRONTEND_URL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True, # Critical for accepting cookies!
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Extract User securely from HTTP-Only Cookie
def get_current_user(session_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing session cookie. Please log in.")
        
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=["HS256"])
        user_email = payload.get("sub")
        
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found.")
            
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token.")


@app.get("/api/briefings")
def generate_meeting_briefings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"🚀 API Request received for user: {current_user.email}")
    try:
        creds = get_user_credentials(current_user)
        meetings = get_today_meetings(creds)
        
        if not meetings:
            return {"message": "No meetings scheduled for today.", "briefings": []}

        briefings_data = []

        for meeting in meetings:
            title = meeting['title']
            time = meeting['start_time']
            attendees = meeting['attendees']
            
            cached_briefing = db.query(BriefingCache).filter(
                BriefingCache.user_id == current_user.id,
                BriefingCache.title == title,
                BriefingCache.time == time
            ).first()
            
            if cached_briefing:
                print(f"⚡ CACHE HIT: Returning saved briefing for: {title}")
                if cached_briefing.attendees and cached_briefing.attendees != "None":
                    attendee_list = [email.strip() for email in cached_briefing.attendees.split(",")]
                else:
                    attendee_list = []
                    
                briefings_data.append({
                    "title": cached_briefing.title,
                    "time": cached_briefing.time,
                    "attendees": attendee_list,
                    "ai_briefing": cached_briefing.ai_briefing
                })
                continue 

            email_context = "No external attendees to fetch context for."
            if attendees:
                email_context = get_email_context(creds, attendees, days_back=14, max_results=5)
            
            prompt = f""" 
            You are an elite, highly organized executive assistant. Your job is to prepare your boss for an upcoming meeting based on calendar data and recent email history.
            
            MEETING DETAILS:
            - Title: {title}
            - Time: {time}
            - Attendees: {', '.join(attendees) if attendees else 'None listed'}
            
            RECENT EMAIL HISTORY WITH ATTENDEES:
            {email_context}
            
            INSTRUCTIONS:
            Provide a concise, professional briefing for this meeting. Include:
            1. Context: A 1-2 sentence summary of what this meeting is likely about based on the email history.
            2. Talking Points: Bullet points of key topics recently discussed in the emails.
            3. If the "RECENT EMAIL HISTORY" says there are no recent emails or no attendees, simply state: "Standard calendar event. No recent email context found." Do not invent information.
            
            Format it cleanly for quick reading.
            """
            
            response = client.models.generate_content(model='gemini-3.1-flash-lite', contents=[prompt])
            
            new_cache_entry = BriefingCache(
                user_id=current_user.id,
                title=title,
                time=time,
                attendees=", ".join(attendees) if attendees else "None",
                ai_briefing=response.text
            )
            
            db.add(new_cache_entry)
            
            briefings_data.append({
                "title": title,
                "time": time,
                "attendees": attendees,
                "ai_briefing": response.text
            })
            
            print(f"✅ Processed briefing for: {title}")

        db.commit()
        return {"message": "Success", "briefings": briefings_data}

    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
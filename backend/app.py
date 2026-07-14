import os
from dotenv import load_dotenv
import google.genai as genai
from fastapi import FastAPI, HTTPException,Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import our custom data pipelines
from calendar_service import get_today_meetings
from gmail_service import get_email_context
from database import engine, SessionLocal, Base, BriefingCache

load_dotenv() 

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=API_KEY)
# Initialize the database tables (Creates briefings.db if it doesn't exist)
Base.metadata.create_all(bind=engine)

#  Initialize the FastAPI app
app = FastAPI(title="AI Executive Assistant API")
# Read the allowed frontend origin, default to localhost if missing
FRONTEND_URL = os.getenv("FRONTEND_URL", )

#  Add CORS Middleware so React can communicate with it safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Allows all origins (we will lock this down to localhost in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],
)
# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# 3. Create our API Endpoint
@app.get("/api/briefings")
def generate_meeting_briefings(db: Session = Depends(get_db)):
    print("🚀 API Request received: Fetching meetings...")
    try:
        meetings = get_today_meetings()
        if not meetings:
            return {"message": "No meetings scheduled for today.", "briefings": []}

        briefings_data = []

        for meeting in meetings:
            title = meeting['title']
            time = meeting['start_time']
            attendees = meeting['attendees']
            # CHECK THE CACHE FIRST
            # title and time used as a unique identifier for the meeting
            cached_briefing = db.query(BriefingCache).filter(
                BriefingCache.title == title,
                BriefingCache.time == time
            ).first()
            if cached_briefing:
                print(f"⚡ CACHE HIT: Returning saved briefing for: {title}")
                if cached_briefing.attendees and cached_briefing.attendees != "None":
                    # Split the string by comma to recreate the array
                    attendee_list = [email.strip() for email in cached_briefing.attendees.split(",")]
                else:
                    attendee_list = []
                briefings_data.append({
                    "title": cached_briefing.title,
                    "time": cached_briefing.time,
                    "attendees": attendee_list,
                    "ai_briefing": cached_briefing.ai_briefing
                })
                continue # Skip the AI generation and move to the next meeting

            # CACHE MISS: Run the AI Pipeline
            
            email_context = "No external attendees to fetch context for."
            if attendees:
                email_context = get_email_context(attendees, days_back=14, max_results=5)
            
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
            
            # Generate AI content
            response = client.models.generate_content(model='gemini-3.1-flash-lite', contents=[prompt])
            # Create a new database record (Assuming 'attendees' in DB is a string)
            new_cache_entry = BriefingCache(
                title=title,
                time=time,
                attendees=", ".join(attendees) if attendees else "None",
                ai_briefing=response.text
            )
            
            # Add to the SQLAlchemy session
            db.add(new_cache_entry)
            
            # Instead of printing, we append it to a dictionary
            briefings_data.append({
                "title": title,
                "time": time,
                "attendees": attendees,
                "ai_briefing": response.text
            })
            
            print(f"✅ Processed briefing for: {title}")

        # Return the final JSON payload
        db.commit()  # Commit all new cache entries to the database
        return {"message": "Success", "briefings": briefings_data}

    except Exception as e:
        print(f"❌ API Error: {e}")
        # If something crashes, send a 500 Server Error back to the frontend
        raise HTTPException(status_code=500, detail=str(e))
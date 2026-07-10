import os
from dotenv import load_dotenv
import google.genai as genai
from calendar_service import get_today_meetings
from gmail_service import get_email_context
load_dotenv()  # Load environment variables from .env file
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
client=genai.Client(api_key=API_KEY)
def generate_meeting_briefings():
    print("Initializing AI execution...")
    #get today's meetings
    meetings=get_today_meetings()
    if not meetings:
        print("No meetings scheduled for today.")
        return
    for meeting in meetings:
        title = meeting['title']
        time = meeting['start_time']
        attendees = meeting['attendees']

        print(f"\n{'='*60}")
        print(f"📅 Analyzing Meeting: {title}")
        print(f"{'='*60}")
        
        # Step C: Fetch relevant email context
        email_context = "No external attendees to fetch context for."
        if attendees:
            email_context = get_email_context(attendees, days_back=14, max_results=5)
        prompt=f""" 
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
        try:
            response=client.models.generate_content(model='gemini-2.5-flash', contents=[prompt])
            print("\n🤖 AI EXECUTIVE BRIEFING:")
            print(response.text)
        except Exception as e:
            print(f"\n❌ Error generating AI briefing: {e}")
if __name__ == '__main__':
    generate_meeting_briefings()
    

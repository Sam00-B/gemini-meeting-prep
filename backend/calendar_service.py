import datetime
from googleapiclient.discovery import build
from auth import authenticate_google_workspace
def get_today_meetings()->list:
    """
    Fetches remaining meetings for today from the user's primary Google Calendar.
    Extracts the title, time, and attendee emails for LLM context.
    """
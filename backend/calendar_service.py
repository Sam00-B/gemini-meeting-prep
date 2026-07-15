import datetime
from googleapiclient.discovery import build

def get_today_meetings(creds) -> list:
    """
    Fetches remaining meetings for today from the user's primary Google Calendar.
    Extracts the title, time, and attendee emails for LLM context.
    Expects a valid google.oauth2.credentials.Credentials object.
    """
    service = build('calendar', 'v3', credentials=creds)
    
    # Calculate time boundaries (Now until end of the current day UTC)
    now = datetime.datetime.now(datetime.UTC)
    end_of_day = now.replace(hour=23, minute=59, second=59)
    time_min = now.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    time_max = end_of_day.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    
    print("Fetching today's upcoming events...")
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
        return []
        
    structured_meetings = []
    for event in events:
        # Skip events that you declined
        if any(attendee.get('self') and attendee.get('responseStatus') == 'declined' for attendee in event.get('attendees', [])):
            continue
            
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        # Extract attendee emails
        attendees = [
            person.get('email') for person in event.get('attendees', [])
            if not person.get('self') and person.get('email')
        ]
        
        meeting_data = {
            'title': event.get('summary', 'No Title'),
            'start_time': start,
            'attendees': attendees
        }
        structured_meetings.append(meeting_data)
        print(f"Meeting: {meeting_data['title']}, Start Time: {meeting_data['start_time']}, Attendees: {', '.join(meeting_data['attendees'])}")
        
    return structured_meetings

if __name__ == "__main__":
    print("⚠️ Testing requires passing a valid credentials object now.")
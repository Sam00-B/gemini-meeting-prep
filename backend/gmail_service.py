from googleapiclient.discovery import build
from auth import authenticate_google_workspace

def get_email_context(attendee_emails: list, days_back=14, max_results=5) -> str:
    """
    Searches Gmail for recent conversations with the provided attendees.
    Uses an optimized Batch Request to fetch all contexts in a single network call.
    """
    if not attendee_emails:
        return "No external attendees to fetch context for."

    creds = authenticate_google_workspace()
    service = build('gmail', 'v1', credentials=creds)

    # 1. Build the query
    email_queries = [f"from:{email} OR to:{email}" for email in attendee_emails]
    combined_query = f"({' OR '.join(email_queries)}) newer_than:{days_back}d"
    
    print(f"Searching Gmail: {combined_query}")

    try:
        # Get the index list (Network Call #1)
        results = service.users().messages().list(
            userId='me', 
            q=combined_query, 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return "No recent email context found with these attendees."

        context_blocks = []

        # Define the callback function for the batch processor
        def process_email_response(request_id, response, exception):
            if exception is not None:
                print(f"❌ Error fetching an email payload: {exception}")
                return
            
            headers = {header['name']: header['value'] for header in response['payload']['headers']}
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown Sender')
            recipient = headers.get('To', 'Unknown Recipient')
            date = headers.get('Date', 'Unknown Date')
            snippet = response.get('snippet', '')

            context_blocks.append(
                f"- Date: {date}\n"
                f"  From: {sender}\n"
                f"  To: {recipient}\n"
                f"  Subject: {subject}\n"
                f"  Preview: {snippet}...\n"
            )

        # Construct and execute the Batch Request (Network Call #2)
        batch = service.new_batch_http_request()
        
        for msg in messages:
            request = service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='metadata', 
                metadataHeaders=['Subject', 'Date', 'From', 'To']
            )
            batch.add(request, callback=process_email_response)
            
        batch.execute() 
        
        return "\n".join(context_blocks)

    except Exception as e:
        print(f"❌ Error fetching Gmail context: {e}")
        return "Error retrieving emails."

if __name__ == '__main__':
    # Test the optimized pipeline
    test_attendees = ['test@example.com'] # Replace with a real email
    context = get_email_context(test_attendees)
    
    print("\n--- BATCH EXTRACTED CONTEXT ---")
    print(context)
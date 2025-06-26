from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

# Gmail API scope for read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def authenticate_gmail():
    # Create OAuth flow and run local server
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Build Gmail service
    service = build('gmail', 'v1', credentials=creds)
    return service


def fetch_emails(service, max_results=5):
    # Fetch latest email message IDs
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
        return

    for msg in messages:
        msg_id = msg['id']
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()

        # Decode raw message
        msg_str = base64.urlsafe_b64decode(msg_detail['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)

        subject = mime_msg['subject']
        sender = mime_msg['from']

        print("\n📩 Email")
        print(f"From: {sender}")
        print(f"Subject: {subject}")

        # Get plain text email content
        for part in mime_msg.walk():
            if part.get_content_type() == "text/plain":
                print("Body:")
                print(part.get_payload(decode=True).decode('utf-8', errors='ignore'))
                break


def main():
    service = authenticate_gmail()
    fetch_emails(service)


if __name__ == '__main__':
    main()

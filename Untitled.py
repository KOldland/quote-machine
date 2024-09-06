from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Define the scopes required for Google Docs API
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = '/Users/krisoldland/Desktop/Quote Machine/quote-machine-425319-f3af2763e04a.json'   # Update with the correct path

# Authenticate using the service account
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
docs_service = build('docs', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

# Create a new Google Doc
document = docs_service.documents().create(body={'title': 'Formatting Test Document'}).execute()
document_id = document['documentId']
print(f"Created document with ID: {document_id}")

# Define the text and formatting you want to apply
text = "This is a test for applying formatting in Google Docs."
requests = [
    # Insert the text
    {
        'insertText': {
            'location': {
                'index': 1  # Index 1 ensures text is inserted at the start of the document
            },
            'text': text
        }
    },
    # Apply formatting (bold)
    {
        'updateTextStyle': {
            'range': {
                'startIndex': 1,  # Starting index of the text
                'endIndex': 1 + len(text)  # Ending index of the text
            },
            'textStyle': {
                'bold': True,
                'fontSize': {'magnitude': 12, 'unit': 'PT'},
                'foregroundColor': {'color': {'rgbColor': {'red': 1, 'green': 0, 'blue': 0}}}
            },
            'fields': 'bold,fontSize,foregroundColor'
        }
    }
]

# Send the requests to Google Docs API to apply the changes
docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

# Grant Editor permissions to your Google account
user_email = 'fieldservicenews@gmail.com'  # Replace with your Google account email
permission = {
    'type': 'user',
    'role': 'writer',  # 'writer' gives editor access
    'emailAddress': user_email
}

drive_service.permissions().create(
    fileId=document_id,
    body=permission,
    fields='id',
).execute()

print(f"Formatting applied to document with ID: {document_id}")
print(f"Editor permissions granted to {user_email}")
print(f"Document link: https://docs.google.com/document/d/{document_id}/edit")

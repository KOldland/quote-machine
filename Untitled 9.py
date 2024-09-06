import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from PIL import Image
from io import BytesIO
import requests

# Define the scopes for both Google Sheets and Google Docs APIs
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = '/Users/krisoldland/Desktop/Quote Machine/quote-machine-425319-f3af2763e04a.json'

# Authenticate and create the service
print("Authenticating...")
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
docs_service = build('docs', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)
print("Authenticated successfully.")

# Open the Google Sheets document by ID
spreadsheet_id = '1gscALSOGoaEYyuUN0zyu_pRAMvjjJvWjv3ZnAFCd5rQ'
print("Loading data from Google Sheets...")
sheet = gc.open_by_key(spreadsheet_id).sheet1
data = pd.DataFrame(sheet.get_all_records())

print("Data loaded from Google Sheets successfully.")
print(data.head())  # Print the first few rows for verification

# Function to calculate totals based on prefixes
def calculate_total(prefix):
    try:
        total = data.loc[data['Line Code'].str.startswith(prefix) & (data['Include'] == 'Y'), 'Total Cost'].sum()
        print(f"Total for {prefix}: £{total:.2f}")
        return total
    except Exception as e:
        print(f"An error occurred while calculating total for {prefix}: {e}")
        return 0
    
# Function to generate text replacements based on the 'description' column
def generate_text_replacements():
    text_replacements = []
    for index, row in data.iterrows():
        placeholder = f"<{row['Line Code']}>"
        if row['Include'] == 'Y':
            combined_description = str(row['description']) if pd.notna(row['description']) else ''
            print(f"Replacing placeholder '{placeholder}' with: '{combined_description}'")
            text_replacements.append({
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder,
                        'matchCase': True
                    },
                    'replaceText': combined_description
                }
            })
        else:
            print(f"Replacing placeholder '{placeholder}' with an empty string.")
            text_replacements.append({
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder,
                        'matchCase': True
                    },
                    'replaceText': ''  # Replace the placeholder with an empty string
                }
            })
            
    return text_replacements

def remove_empty_paragraphs_in_tables(document_id):
    # Fetch the document content
    document = docs_service.documents().get(documentId=document_id).execute()
    requests = []
    
    # Iterate through the document content
    for element in document.get('body', {}).get('content', []):
        if 'table' in element:
            table = element['table']
            for row in table.get('tableRows', []):
                for cell in row.get('tableCells', []):
                    for cell_content in cell.get('content', []):
                        if 'paragraph' in cell_content:
                            paragraph = cell_content['paragraph']
                            paragraph_text = ""
                            
                            # Check each element in the paragraph
                            for elem in paragraph.get('elements', []):
                                if 'textRun' in elem:
                                    text = elem['textRun'].get('content', '')
                                    # Accumulate text after stripping whitespace, invisible characters, and non-breaking spaces
                                    paragraph_text += text.strip().replace("\u200B", "").replace("\uFEFF", "").replace("\xa0", "")
                                    
                            # Debugging output to see what's inside the paragraph
                            print(f"Paragraph text after stripping: '{paragraph_text}' (Length: {len(paragraph_text)})")
                            
                            # Consider the paragraph empty if it has zero or one character
                            if len(paragraph_text) <= 1:
                                print(f"Marking paragraph for deletion: '{paragraph_text}'")
                                start_index = cell_content['startIndex']
                                end_index = cell_content['endIndex']
                                requests.append({
                                    'deleteContentRange': {
                                        'range': {
                                            'startIndex': start_index,
                                            'endIndex': end_index
                                        }
                                    }
                                })
                                
    # Execute batchUpdate to remove empty paragraphs within tables
    if requests:
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
    print("Empty paragraphs within tables have been deleted.")
    
# Template document ID
template_document_id = '1ciAFVZC3Gqn5wN7SckY8zkZfMihkwh6j1jZoMDwdd30'

# Function to copy the template and create a new document
def copy_template(file_id, new_title):
    body = {'name': new_title}
    try:
        print(f"Copying template with ID: {file_id}")
        new_document = drive_service.files().copy(
            fileId=file_id,
            body=body,
            supportsAllDrives=True
        ).execute()
        print(f"New document created with ID: {new_document.get('id')}")
        return new_document.get('id')
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
# Function to create and populate a Google Doc
def create_google_doc(template_document_id, form_data):
    new_document_id = copy_template(template_document_id, form_data['cd1'] if form_data['cd1'] else 'New Document')
    if not new_document_id:
        print("Failed to create a new document.")
        return
    
    print("Before generating text replacements...")
    # Generate text replacement requests
    text_replacements = generate_text_replacements()
    print("After generating text replacements...")
    
    # Execute the batchUpdate request to populate the document
    try:
        result = docs_service.documents().batchUpdate(documentId=new_document_id, body={'requests': text_replacements}).execute()
        print("Document update requests executed successfully.")
    except Exception as e:
        print(f"An error occurred during document update: {e}")
        
    # Set the permissions to allow editing
    permission = {
        'type': 'user',
        'role': 'writer',  # Change to 'editor' if full edit access is needed
        'emailAddress': 'fieldservicenews@gmail.com'
    }
    try:
        drive_service.permissions().create(fileId=new_document_id, body=permission).execute()
        print(f"Writer permission granted to 'fieldservicenews@gmail.com'.")
    except Exception as e:
        print(f"An error occurred while setting permissions: {e}")
        
    return new_document_id

# Form data to be populated in the document
form_data = {
    'cd1': '<cd1>',
    'todays_date': pd.Timestamp.today().strftime('%Y-%m-%d')
}

# Create and populate the Google Doc
new_doc_id = create_google_doc(template_document_id, form_data)
print(f"New document created with ID: {new_doc_id}")
print(f"Document link: https://docs.google.com/document/d/{new_doc_id}/edit")

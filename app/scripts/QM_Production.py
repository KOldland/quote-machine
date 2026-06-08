import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from PIL import Image
from io import BytesIO
import requests
import os
from pathlib import Path

# Define the scopes for both Google Sheets and Google Docs APIs
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

# Load credentials path from environment first, with local app fallback
SERVICE_ACCOUNT_FILE = os.getenv(
    'QM_CREDENTIALS_PATH',
    str(Path(__file__).resolve().parents[1] / 'QM_credentials.json')
)
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(
        'Google credentials file not found. Set QM_CREDENTIALS_PATH or place QM_credentials.json in the app directory.'
    )

# Authenticate and create the service
print("Authenticating...")
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
docs_service = build('docs', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)
print("Authenticated successfully.")

# Open the Google Sheets document by ID
spreadsheet_id = os.getenv('QM_SPREADSHEET_ID', '1gscALSOGoaEYyuUN0zyu_pRAMvjjJvWjv3ZnAFCd5rQ')
print("Loading data from Google Sheets...")
sheet = gc.open_by_key(spreadsheet_id).sheet1
data = pd.DataFrame(sheet.get_all_records())

print("Data loaded from Google Sheets successfully.")
print(data.head())  # Print the first few rows for verification
    
# Function to generate text replacements based on the 'description' column
def generate_text_replacements(document_id):
    text_replacements = []
    previous_line_break = False  # Track if the last replacement added a line break
    
    for index, row in data.iterrows():
        placeholder = f"<{row['Line Code']}>"
        if row['Include'] == 'Y':
            description = str(row['description']) if pd.notna(row['description']) else ''
            
            # Check if the placeholder is for an image (e.g., img1, img2, etc.)
            if row['Line Code'].startswith('img'):
                image_url = description  # Image URL is stored in the description column
                if pd.notna(image_url):  # If there's a valid image URL
                    print(f"Inserting image for placeholder {placeholder} from URL: {image_url}")
                    insert_image_at_placeholder(document_id, placeholder, image_url)
                continue  # Skip text replacement for image placeholders
            
            # Normal text replacement for non-image placeholders
            print(f"Replacing placeholder '{placeholder}' with: '{description}'")
            
            # Determine formatting options based on special characters
            is_bullet = '^' in placeholder
            is_single_break = '#' in placeholder
            is_remove_preceding_break = '*' in placeholder
            is_no_break = '@' in placeholder
            
            if is_bullet:
                description = f"• {description}"  # Add bullet point
                line_breaks = '\n'  # Single line break after bullet point
            elif is_single_break:
                line_breaks = '\n'  # Single line break after string
            elif is_remove_preceding_break:
                if previous_line_break:
                    # Remove the last line break
                    text_replacements[-1]['replaceAllText']['replaceText'] = text_replacements[-1]['replaceAllText']['replaceText'].rstrip('\n')
                line_breaks = '\n\n'  # Double line break after string
            elif is_no_break:
                line_breaks = ''  # No line breaks added
            else:
                line_breaks = '\n\n'  # Double line break after string
                
            # Track if the last replacement added a line break
            previous_line_break = line_breaks != ''
            
            # Apply the replacement
            final_placeholder = placeholder.replace('#', '').replace('*', '').replace('^', '').replace('@', '')
            print(f"Final placeholder for replacement: {final_placeholder}, Text: {description + line_breaks}")
            
            text_replacements.append({
                'replaceAllText': {
                    'containsText': {
                        'text': final_placeholder,  # Remove the special characters
                        'matchCase': True
                    },
                    'replaceText': description + line_breaks
                }
            })
        else:
            print(f"Replacing placeholder '{placeholder}' with an empty string.")
            text_replacements.append({
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder.replace('#', '').replace('*', '').replace('^', '').replace('@', ''),  # Remove the special characters
                        'matchCase': True
                    },
                    'replaceText': ''  # Replace the placeholder with an empty string
                }
            })
            previous_line_break = False  # No line break added
            
    print(f"Total replacements generated: {len(text_replacements)}")
    return text_replacements


# Function to insert image at the correct placeholder location with specific dimensions
def insert_image_at_placeholder(document_id, placeholder, image_url):
    # Define dimensions for specific image placeholders (inverted width and height where requested)
    image_dimensions = {
        'img1': {'width': 415, 'height': 818},
        'img2': {'width': 530, 'height': 660},
        'img15': {'width': 130, 'height': 670},
        'img16': {'width': 130, 'height': 670},
        'img17': {'width': 130, 'height': 670},
        'img18': {'width': 130, 'height': 670},
        'img4': {'width': 200, 'height': 670},
        'img5': {'width': 200, 'height': 670},
        'img6': {'width': 200, 'height': 670},
        'img7': {'width': 400, 'height': 670},
        'img19': {'width': 400, 'height': 670},
        'img22': {'width': 270, 'height': 670}
    }
    
    # Check if the placeholder exists in the image_dimensions dictionary
    if placeholder in image_dimensions:
        width = image_dimensions[placeholder]['width']
        height = image_dimensions[placeholder]['height']
    else:
        # Default dimensions if the placeholder is not defined
        width = 500
        height = 300
        
    try:
        # Fetch the document content to get the index of the placeholder
        document = docs_service.documents().get(documentId=document_id).execute()
        content = document.get('body').get('content', [])
        
        # Find the location of the placeholder
        for element in content:
            if 'paragraph' in element:
                paragraph = element.get('paragraph')
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_run = elem.get('textRun')
                        if placeholder in text_run.get('content', ''):
                            # Get the location index of the placeholder
                            location_index = elem['startIndex']
                            
                            # Create the image insertion request with specified dimensions
                            requests = [
                                {
                                    'replaceAllText': {
                                        'containsText': {
                                            'text': placeholder,
                                            'matchCase': True
                                        },
                                        'replaceText': ''  # Replace the placeholder with an empty string
                                    }
                                },
                                {
                                    'insertInlineImage': {
                                        'location': {
                                            'index': location_index
                                        },
                                        'uri': image_url,
                                        'objectSize': {
                                            'height': {
                                                'magnitude': height,  # Use the defined height
                                                'unit': 'PT'
                                            },
                                            'width': {
                                                'magnitude': width,  # Use the defined width
                                                'unit': 'PT'
                                            }
                                        }
                                    }
                                }
                            ]
                            
                            # Execute the batchUpdate request to replace the placeholder and insert the image
                            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
                            print(f"Image inserted at placeholder {placeholder} with size {width}x{height}.")
                            return
        print(f"Placeholder {placeholder} not found for image insertion.")
        
    except Exception as e:
        print(f"An error occurred while inserting the image for {placeholder}: {e}")
        
# Inserting images inline with the text, based on placeholders in the description column
def insert_images_from_description(document_id):
    for index, row in data.iterrows():
        placeholder = row['Line Code']  # e.g., img1, img2, etc.
        if placeholder.startswith('img'):  # If the Line Code contains an image placeholder
            image_url = row['description']  # Fetch the image URL from the description column
            if pd.notna(image_url):  # If there is a valid image URL
                print(f"Inserting image for placeholder {placeholder} from URL: {image_url}")
                placeholder_in_template = f"<{placeholder}>"  # In the template, placeholders are in angular brackets
                insert_image_at_placeholder(document_id, placeholder_in_template, image_url)
            else:
                print(f"No valid URL for {placeholder}, skipping.")
# Function to remove empty paragraphs and tables
def remove_empty_paragraphs_and_tables(document_id):
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
        elif 'paragraph' in element:
            paragraph = element['paragraph']
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
                start_index = element['startIndex']
                end_index = element['endIndex']
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
    # Extract the client address from the description column where the Line Code is 'cd1'
    client_address_row = data.loc[data['Line Code'] == 'cd1']
    if not client_address_row.empty:
        client_address = client_address_row.iloc[0]['description']
    else:
        client_address = 'New Document'  # Fallback title if no address found
        
    # Now use the client_address as the new document title
    new_document_id = copy_template(template_document_id, client_address)
    
    if not new_document_id:
        print("Failed to create a new document.")
        return
    
    print("Before generating text replacements...")
    # Generate text replacement requests
    text_replacements = generate_text_replacements(new_document_id)
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
        
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
                            
                            # Create the image insertion request with specified dimensions and universal formatting
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
                                },
                                {
                                    'updateImageProperties': {
                                        'objectId': f"image_{location_index}",  # Use a dynamic ID
                                        'imageProperties': {
                                            'contentUri': image_url,
                                            'objectSize': {
                                                'width': {
                                                    'magnitude': width,
                                                    'unit': 'PT'
                                                },
                                                'height': {
                                                    'magnitude': height,
                                                    'unit': 'PT'
                                                }
                                            },
                                            'layoutMode': 'FIX_POSITION',
                                            'alignment': 'CENTER',
                                            'wrapText': 'BREAK_TEXT'
                                        },
                                        'fields': 'size,alignment,wrapText'
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

# Other existing functions for removing paragraphs, creating the doc, etc., remain the same

# Form data to be populated in the document
form_data = {
    'cd1': '<cd1>',
    'todays_date': pd.Timestamp.today().strftime('%Y-%m-%d')
}

# Create and populate the Google Doc
new_doc_id = create_google_doc(template_document_id, form_data)
print(f"New document created with ID: {new_doc_id}")
print(f"Document link: https://docs.google.com/document/d/{new_doc_id}/edit")

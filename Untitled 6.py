# 1. Imports

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from PIL import Image
from io import BytesIO
import requests

# 2. Define Utility Functions

# Function to retrieve and log document content
def get_document_content(service, document_id):
	document = service.documents().get(documentId=document_id).execute()
	content = document.get('body').get('content', [])
	
	text = ""
	for element in content:
		if 'paragraph' in element:
			for paragraph_element in element.get('paragraph').get('elements', []):
				text += paragraph_element.get('textRun', {}).get('content', "")
	return text

# Function to find the start and end indices of a text segment within the document
def find_text_indices(full_text, search_text):
	start_index = full_text.find(search_text)
	end_index = start_index + len(search_text)
	return start_index, end_index

# Updated function to apply formatting with recalculated indices
def apply_formatting_with_correct_indices(service, document_id, text_to_format, formatting):
	# Retrieve the document content after text insertion
	document_content = get_document_content(service, document_id)
	
	# Find the correct indices
	start_index, end_index = find_text_indices(document_content, text_to_format)
	
	# Check if indices are valid
	if start_index == -1:
		print(f"Text '{text_to_format}' not found in document.")
		return
	
	# Prepare the formatting request
	requests = [
		{
			'updateTextStyle': {
				'range': {
					'startIndex': start_index,
					'endIndex': end_index
				},
				'textStyle': formatting,
				'fields': ','.join(formatting.keys())
			}
		}
	]
	
	# Apply formatting
	try:
		service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
		print(f"Applied formatting to '{text_to_format}' from index {start_index} to {end_index}.")
	except Exception as e:
		print(f"An error occurred while applying formatting: {e}")
		
# 3. Define scopes
		
# Define the scopes for both Google Sheets and Google Docs APIs
SCOPES = [
	'https://www.googleapis.com/auth/spreadsheets.readonly',
	'https://www.googleapis.com/auth/documents',
	'https://www.googleapis.com/auth/drive'
]

# 4. Service Account 

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = '/Users/krisoldland/Desktop/Quote Machine/quote-machine-425319-f3af2763e04a.json'

# Authenticate and create the service
print("Authenticating...")
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
docs_service = build('docs', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)
print("Authenticated successfully.")
print("Credentials valid:", credentials.valid)
print("Credentials expire at:", credentials.expiry)

# Open the Google Sheets document by ID
spreadsheet_id = '1AdgsZ1HPAFYempFjFau1qzNdcjapZ22iHdvJzGbTEKg'
print("Loading data from Google Sheets...")
sheet = gc.open_by_key(spreadsheet_id).sheet1
data = pd.DataFrame(sheet.get_all_records())

# Ensure 'Total Cost' column is numeric and fill NaN values with 0
data['Total Cost'] = pd.to_numeric(data['Total Cost'], errors='coerce').fillna(0)

print("Data loaded from Google Sheets successfully.")
print(data.head())  # Print the first few rows for verification

# Define formatting rules
FORMATTING = {
	'Description1': {
		'bold': True,
		'fontSize': {'magnitude': 11, 'unit': 'PT'},
		'foregroundColor': {'color': {'rgbColor': {'red': 1, 'green': 0, 'blue': 0}}}  # Red color
	},
	'Description2': {
		'bold': True,
		'fontSize': {'magnitude': 11, 'unit': 'PT'},
		'foregroundColor': {'color': {'rgbColor': {'red': 0, 'green': 0, 'blue': 0}}}  # Black color
	},
	'Description3': {
		'fontSize': {'magnitude': 11, 'unit': 'PT'},
		'foregroundColor': {'color': {'rgbColor': {'red': 0, 'green': 0, 'blue': 0}}}  # Black color
	},
	'Description4': {
		'italic': True,
		'fontSize': {'magnitude': 8, 'unit': 'PT'},
		'foregroundColor': {'color': {'rgbColor': {'red': 0, 'green': 0, 'blue': 1}}}  # Blue color
	},
	'Description5': {
		'italic': True,
		'fontSize': {'magnitude': 6, 'unit': 'PT'},
		'foregroundColor': {'color': {'rgbColor': {'red': 0, 'green': 0, 'blue': 1}}}  # Blue color
	}
}

# Function to calculate totals based on prefixes
def calculate_total(prefix):
	try:
		total = data.loc[data['Line Code'].str.startswith(prefix) & (data['Include'] == 'Y'), 'Total Cost'].sum()
		print(f"Total for {prefix}: £{total:.2f}")
		return total
	except Exception as e:
		print(f"An error occurred while calculating total for {prefix}: {e}")
		return 0
	
# Function to generate combined text with cost
def generate_combined_text_with_cost(prefix):
	combined_text = []
	for index, row in data.iterrows():
		if row['Include'] == 'Y' and row['Line Code'].startswith(prefix):
			descriptions = [row[col] for col in ['Description1', 'Description2', 'Description3', 'Description4', 'Description5'] if pd.notna(row[col])]
			total_cost = row['Total Cost']
			combined_text.append(' '.join(descriptions).replace("<total_cost>", f"£{total_cost:.2f}"))
	return "\n".join(combined_text)

# Function to check if an image is landscape
def is_landscape(url):
	response = requests.get(url)
	img = Image.open(BytesIO(response.content))
	return img.width > img.height

# Function to generate image requests
def generate_image_requests(img_placeholders, img_urls):
	image_requests = []
	grid_width = 500  # Width in pixels for each row of images
	min_margin = 3  # Minimum margin between images in pixels
	row_height_ratio = 0.25  # Ratio of height to width for each image row
	
	landscape_urls = [url for url in img_urls if is_landscape(url)]
	portrait_urls = [url for url in img_urls if not is_landscape(url)]
	
	images = []
	i = 0
	while i < len(img_urls):
		row = []
		if len(landscape_urls) > 0 and len(portrait_urls) > 1:
			row.append(landscape_urls.pop(0))
			row.append(portrait_urls.pop(0))
			row.append(portrait_urls.pop(0))
		elif len(landscape_urls) > 1:
			row.append(landscape_urls.pop(0))
			row.append(landscape_urls.pop(0))
		elif len(portrait_urls) > 2:
			row.append(portrait_urls.pop(0))
			row.append(portrait_urls.pop(0))
			row.append(portrait_urls.pop(0))
		elif len(portrait_urls) > 0 or len(landscape_urls) > 0:
			row.extend(portrait_urls if len(portrait_urls) > 0 else landscape_urls)
		images.append(row)
		i += len(row)
		
	for row in images:
		row_width = grid_width - (len(row) - 1) * min_margin
		img_widths = [int(row_width / len(row))] * len(row)
		for url, placeholder in zip(row, img_placeholders[:len(row)]):
			response = requests.get(url)
			img = Image.open(BytesIO(response.content))
			img = img.resize((img_widths.pop(0), int(img_widths[0] * row_height_ratio)))
			image_requests.append({
				'insertInlineImage': {
					'uri': url,
					'objectSize': {
						'height': {'magnitude': img.height, 'unit': 'PT'},
						'width': {'magnitude': img.width, 'unit': 'PT'},
					},
					'location': {
						'index': 1,  # Insert the image at the start of the document; adjust as needed
					}
				}
			})
	return image_requests

# Template document ID
template_document_id = '1gUHdxLkC36GrJsQFP3oMOO6RLWrcwEz_X1xy1os3uIM'

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
	
# Function to replace unused placeholders with empty text
def replace_unused_placeholders(document_id):
	placeholders_to_check = set([f"<{code}>" for code in data['Line Code']])
	# Identify placeholders that should be replaced because they are not included (marked with 'N')
	unused_placeholders = [placeholder for placeholder in placeholders_to_check if data.loc[data['Line Code'] == placeholder.strip('<>')].iloc[0]['Include'] == 'N']
	print(f"Unused placeholders: {unused_placeholders}")
	
	unused_requests = []
	for placeholder in unused_placeholders:
		unused_requests.append({
			'replaceAllText': {
				'containsText': {'text': placeholder, 'matchCase': True},
				'replaceText': ''
			}
		})
		
	for request in unused_requests:
		print(request)
		
	if unused_requests:
		try:
			result = docs_service.documents().batchUpdate(documentId=document_id, body={'requests': unused_requests}).execute()
			print("Unused placeholders replaced with empty text successfully.")
		except Exception as e:
			print(f"An error occurred while replacing unused placeholders: {e}")
			
# Function to create and populate a Google Doc
def create_google_doc(template_document_id, form_data):
	new_document_id = copy_template(template_document_id, form_data['cd1'] if form_data['cd1'] else 'New Document')
	if not new_document_id:
		print("Failed to create a new document.")
		return
	
	doc_requests = [
		{'replaceAllText': {'containsText': {'text': '<cd1>', 'matchCase': True}, 'replaceText': form_data['cd1']}},
		{'replaceAllText': {'containsText': {'text': '<todays_date>', 'matchCase': True}, 'replaceText': pd.Timestamp.today().strftime('%Y-%m-%d')}}
	]
	
	prefixes = ['si', 'pl', 'bw', 'dw', 'ew', 'er', 'fs', 'ps', 'id', 'dr', 'wp', 'frc', 'el', 'sl', 'vl', 'ac', 'sd', 'gv', 'sw', 'pc']
	totals = {}
	for prefix in prefixes:
		total_placeholder = f"<{prefix}_total>"
		total = calculate_total(prefix)
		totals[prefix] = total
		doc_requests.append({'replaceAllText': {'containsText': {'text': total_placeholder, 'matchCase': True}, 'replaceText': f"£{total:.2f}"}})
		print(f"Replaced {total_placeholder} with £{total:.2f}")
		
		# Generate combined text with cost for the given prefix
		combined_text = generate_combined_text_with_cost(prefix)
		if combined_text:
			combined_placeholder = f"<{prefix}_combined>"
			doc_requests.append({'replaceAllText': {'containsText': {'text': combined_placeholder, 'matchCase': True}, 'replaceText': combined_text}})
			print(f"Replaced {combined_placeholder} with combined text for {prefix}.")
			
	# Generate combined total for combined_total
	combined_prefixes = ['bw', 'dw', 'ew', 'er', 'fs', 'ps']
	combined_total = sum(totals[prefix] for prefix in combined_prefixes)
	doc_requests.append({'replaceAllText': {'containsText': {'text': '<combined_total>', 'matchCase': True}, 'replaceText': f"£{combined_total:.2f}"}})
	print(f"Replaced <combined_total> with £{combined_total:.2f}")
	
	# Generate combined total for combined_total_2
	special_line_codes = ['sww9KCB', 'sww9RCB', 'sww9FRRO', 'sww9GG', 'sww9OP', 'sww9WCSL', 'sww9WCUS', 'sww9RRUWC', 'sww9CFRWS', 'sww9CBNCA', 'sww9UWC', 'sww11PHH']
	special_total = sum(pd.to_numeric(data.loc[data['Line Code'].isin(special_line_codes) & (data['Include'] == 'Y'), 'Total Cost'], errors='coerce').fillna(0))
	combined_total_2 = combined_total + special_total
	doc_requests.append({'replaceAllText': {'containsText': {'text': '<combined_total_2>', 'matchCase': True}, 'replaceText': f"£{combined_total_2:.2f}"}})
	print(f"Replaced <combined_total_2> with £{combined_total_2:.2f}")
	
	# Calculate payments based on combined_total_2
	initial_payment = 0.05 * combined_total_2
	x_payment = (combined_total_2 - initial_payment) * 0.33
	com_meeting_payment = x_payment * 0.5
	third_payment = x_payment * 0.5
	remaining_balance = combined_total_2 - (initial_payment + com_meeting_payment + third_payment)
	other_payments = round(remaining_balance / 7 / 1000) * 1000
	final_payment = remaining_balance - other_payments * 7 - 750
	
	# Insert payments into the document
	payments = [
		{'replaceAllText': {'containsText': {'text': '<initial_payment>', 'matchCase': True}, 'replaceText': f"£{initial_payment:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<com_meeting_payment>', 'matchCase': True}, 'replaceText': f"£{com_meeting_payment:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<first_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<second_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<third_payment>', 'matchCase': True}, 'replaceText': f"£{third_payment:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<fourth_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<fifth_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<sixth_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<seventh_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<eighth_payment>', 'matchCase': True}, 'replaceText': f"£{other_payments:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<ninth_payment>', 'matchCase': True}, 'replaceText': f"£{final_payment:.2f}"}},
		{'replaceAllText': {'containsText': {'text': '<tenth_payment>', 'matchCase': True}, 'replaceText': f"£750"}}
	]
	doc_requests.extend(payments)
	print("Inserted payment details into the document.")
	
	# Add replacement requests for specific line code strings (Description1 to Description5)
	for index, row in data.iterrows():
		if row['Include'] == 'Y':
			descriptions = []
			for desc_col in ['Description1', 'Description2', 'Description3', 'Description4', 'Description5']:
				if pd.notna(row[desc_col]) and row[desc_col]:
					description = row[desc_col]
					if '<total_cost>' in description:
						description = description.replace('<total_cost>', f"£{row['Total Cost']:.2f}")
					descriptions.append(description)
			if descriptions:
				combined_description = " ".join(descriptions)
				placeholder = f"<{row['Line Code']}>"
				doc_requests.append({'replaceAllText': {'containsText': {'text': placeholder, 'matchCase': True}, 'replaceText': f"\n{combined_description}"}})
				
				# Apply formatting to each description segment
				for desc_col in ['Description1', 'Description2', 'Description3', 'Description4', 'Description5']:
					if pd.notna(row[desc_col]) and row[desc_col]:
						description = row[desc_col]
						formatting = FORMATTING[desc_col]
						apply_formatting_with_correct_indices(docs_service, new_document_id, description, formatting)
						
	# Add replacement requests for image placeholders if the column exists
	if 'Image URL' in data.columns:
		img_placeholders = [f'<img{i}>' for i in range(23, 33)]
		img_urls = data.loc[data['Include'] == 'Y', 'Image URL'].dropna().tolist()
		img_requests = generate_image_requests(img_placeholders, img_urls)
		doc_requests.extend(img_requests)
		print("Added image replacement requests.")
		
	# Execute the batchUpdate request to populate the document
	try:
		result = docs_service.documents().batchUpdate(documentId=new_document_id, body={'requests': doc_requests}).execute()
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

# Apply simple formatting directly
def apply_simple_formatting(service, document_id):
	# Example text and formatting
	text = "This is a test for applying formatting in Google Docs."
	requests = [
		# Insert the text
		{
			'insertText': {
				'location': {
					'index': 1  # Insert at the start
				},
				'text': text
			}
		},
		# Apply formatting (bold, font size, color)
		{
			'updateTextStyle': {
				'range': {
					'startIndex': 1,
					'endIndex': 1 + len(text)
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
	
	# Apply the changes
	try:
		service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
		print(f"Applied simple formatting to document with ID: {document_id}")
	except Exception as e:
		print(f"An error occurred while applying simple formatting: {e}")
		
	return document_id  # Ensure this line is inside the function

# Form data to be populated in the document
form_data = {
	'cd1': '<cd1>',
	'todays_date': pd.Timestamp.today().strftime('%Y-%m-%d')
}

# Create and populate the Google Doc
new_doc_id = create_google_doc(template_document_id, form_data)
replace_unused_placeholders(new_doc_id)
print(f"New document created with ID: {new_doc_id}")
print(f"Document link: https://docs.google.com/document/d/{new_doc_id}/edit")

						
		
		
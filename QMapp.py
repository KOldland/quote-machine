#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import gspread
import subprocess
from google.oauth2.service_account import Credentials
import re
from flask_wtf.csrf import CSRFProtect
import os
from flask import jsonify
import re 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename# Import the regular expression module

app = Flask(__name__)
csrf = CSRFProtect(app)

# Define upload folder path
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Set max upload size to 2MB
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
app.config['SESSION_FILE_DIR'] = './flask_session/'  # Create a directory for sessions
app.config['SECRET_KEY'] = 'S)x;:qtD5EC"'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
	os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize the session extension
Session(app)

# Set up Google Sheets API credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Detect if running on local machine or in production
if os.path.exists('/Users/krisoldland/Desktop/Quote_Machine/QM_web_app/QM_credentials.json'):
	# Local environment
	creds_path = '/Users/krisoldland/Desktop/Quote_Machine/QM_web_app/QM_credentials.json'
else:
	# Production environment
	creds_path = 'QM_credentials.json'

# Initialize Google Sheets client
creds = Credentials.from_service_account_file('QM_credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet_id = '1gscALSOGoaEYyuUN0zyu_pRAMvjjJvWjv3ZnAFCd5rQ'
sheet = client.open_by_key(spreadsheet_id).sheet1

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fetch the data without storing too much in session
def fetch_data():
	# You may remove caching here if you prefer not to store this large data
	return sheet.get_all_records()

# Function to check if a line code is included (i.e., marked with 'Y')
def is_included(line_code):
	sheet_data = fetch_data()
	for row in sheet_data:
		if row.get('Line Code') == line_code and row.get('Include') == 'Y':
			return True
	return False

# Helper function to return only alphanumeric characters from line codes
def to_alphanumeric_code(line_code):
	# Remove all non-alphanumeric characters
	return re.sub(r'\W+', '', line_code)


# Function to update 'Include' column based on selected parent and child prefixes using batch updates
def update_include_column(selected_prefixes):
	row_index = None  # Initialize row_index to avoid errors if it's referenced in an exception
	
	try:
		print(f"Selected prefixes: {selected_prefixes}")  # Add this to check the input prefixes
		print("Fetching Google Sheets data...")  # Log fetching step
		sheet_data = fetch_data()
		updates = []  # Collect all updates here
		
		if not sheet_data:
			print("No data fetched from Google Sheets.")
			return  # Early exit if no data is fetched
		
		# Step 1: Identify the selected parent prefixes
		parent_prefixes = [
			to_alphanumeric_code(prefix) for prefix in selected_prefixes 
			if len(to_alphanumeric_code(prefix)) > 1 and to_alphanumeric_code(prefix)[-1].isdigit()
		]
		print(f"Identified parent prefixes: {parent_prefixes}")  # Log identified parent prefixes
		
		selected_sd = session.get('selected_sd', [])
		
		for row_index, row in enumerate(sheet_data, start=2):  # Start from 2 because row 1 is the header
			line_code = row.get('Line Code', '')
			include_status = row.get('Include', '') 
			alphanumeric_code = to_alphanumeric_code(line_code)  # Keep only alphanumeric characters
		
			# Check if line_code or dropdown (selected_sd) matches
			if alphanumeric_code in selected_sd:
				if include_status != 'Y':
					updates.append({
						'range': f'E{row_index}',  # Update column E (Include)
						'values': [['Y']]
				})
					
			# Log the line code being processed for debugging
			print(f"Processing line code: {line_code}, Alphanumeric line code: {alphanumeric_code}")  # Debugging
		
			# Check if the line code is a parent or child
			is_parent = alphanumeric_code[-1].isdigit()  # Parent ends with a number
			is_child = alphanumeric_code[-1].isalpha()  # Child ends with a letter
		
			# If it's a parent and its prefix matches one of the selected prefixes, mark the parent and all children
			if is_parent and alphanumeric_code in parent_prefixes:
				print(f"Marking parent line code: {alphanumeric_code} at row {row_index}")
				
				# Mark the parent
				if include_status != 'Y':
					updates.append({
						'range': f'E{row_index}',  # Column E = Include column
						'values': [['Y']]
					})	
					
				# Find and mark all associated children (same prefix but ends with a letter)
				for child_row_index, child_row in enumerate(sheet_data, start=2):
					child_code = to_alphanumeric_code(child_row.get('Line Code', ''))
					child_include_status = child_row.get('Include', '')
					
					if child_code.startswith(alphanumeric_code) and len(child_code) == len(alphanumeric_code) + 1 and child_code[-1].isalpha():
						print(f"Marking child line code: {child_code} at row {child_row_index}")
						if child_include_status != 'Y':
							updates.append({
								'range': f'E{child_row_index}',
								'values': [['Y']]
					})
							
			# Case 2: If the line code is not selected, mark it as 'N'
			elif is_parent and alphanumeric_code not in selected_prefixes:
				print(f"Marking unselected parent: {alphanumeric_code} as 'N'")
				if include_status != 'N':
					updates.append({
						'range': f'E{row_index}',
						'values': [['N']]
					})
					
				# Mark all children with the same prefix as 'N'
				for child_row_index, child_row in enumerate(sheet_data, start=2):
					child_code = to_alphanumeric_code(child_row.get('Line Code', ''))
					child_include_status = child_row.get('Include', '')
					
					if child_code.startswith(alphanumeric_code) and len(child_code) == len(alphanumeric_code) + 1 and child_code[-1].isalpha():
						print(f"Marking child: {child_code} as 'N'")
						if child_include_status != 'N':
							updates.append({
								'range': f'E{child_row_index}',
								'values': [['N']]
							})
		# Add a checkpoint to confirm that function reaches this point
		print("Completed processing rows, ready to batch update.")
		
		if updates:
			print(f"Prepared updates: {updates}")
			result = sheet.batch_update(updates) 
			print(f"Batch update successful: {result}")
		else:
			print("No updates to send.")
			
	except Exception as e:
		error_row = row_index if row_index is not None else "unknown row"  # Check if row_index has a value
		print(f"Error updating include column at {error_row}: {e}")
		
# Function to update the 'Description' column and "unit Column"
def update_description_column(pd1_manual_input=None, pd2_manual_input=None, pd3_manual_input=None, pd4_manual_input=None, pd5_manual_input=None, pd6_manual_input=None, pd7_manual_input=None, pd8_manual_input=None, pd9_manual_input=None, pd10_manual_input=None,nb1_manual_input=None, nb2_manual_input=None, an1_manual_input=None, an2_manual_input=None, an3_manual_input=None, an4_manual_input=None, an5_manual_input=None, an6_manual_input=None, an7_manual_input=None, dm1_manual_input=None, dm2_manual_input=None, dm3_manual_input=None, dm4_manual_input=None, dm5_manual_input=None, cs1_manual_input=None, ):
	
	try:
		# Fetch the sheet data
		sheet_data = fetch_data()
		
		description_column_index = 11  # Description column (column 11)
		dimensions_column_index = 10  # Dimensions column (column 10)
		unit_input_column_index = 7  # Units column (column 7)
		
		# Iterate over the rows and look for the placeholders in the "Line Code" column
		for row_index, row in enumerate(sheet_data, start=2):  # Start from 2 to skip the header
			line_code = row.get('Line Code', '')
		
			if line_code == 'pd1':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd1_manual_input)
			elif line_code == 'pd2':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd2_manual_input)
			elif line_code == 'pd3':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd3_manual_input)
			elif line_code == 'pd4':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd4_manual_input)
			elif line_code == 'pd5':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd5_manual_input)
			elif line_code == 'pd6':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd6_manual_input)
			elif line_code == 'pd7':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd7_manual_input)
			elif line_code == 'pd8':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd8_manual_input)
			elif line_code == 'pd9':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd9_manual_input)
			elif line_code == 'pd10':  # Handle pd2 dynamically
					sheet.update_cell(row_index, description_column_index, pd10_manual_input)
			elif line_code == 'an1':  
					sheet.update_cell(row_index, description_column_index, an1_manual_input)
			elif line_code == 'an2':  
					sheet.update_cell(row_index, description_column_index, an2_manual_input)
			elif line_code == 'an3':  
					sheet.update_cell(row_index, description_column_index, an3_manual_input)
			elif line_code == 'an4':  
					sheet.update_cell(row_index, description_column_index, an4_manual_input)
			elif line_code == 'an5':  
					sheet.update_cell(row_index, description_column_index, an5_manual_input)
			elif line_code == 'an6':  
					sheet.update_cell(row_index, description_column_index, an6_manual_input)
			elif line_code == 'an7':  
					sheet.update_cell(row_index, description_column_index, an7_manual_input)
			elif line_code == 'nb1#' and nb1_manual_input:
				sheet.update_cell(row_index, description_column_index, nb1_manual_input)
			elif line_code == 'nb2#' and nb2_manual_input:
				sheet.update_cell(row_index, description_column_index, nb2_manual_input)
			elif line_code == 'dm1@' and dm1_manual_input:
				sheet.update_cell(row_index, dimensions_column_index, dm1_manual_input)
			elif line_code == 'dm2@' and dm2_manual_input:
				sheet.update_cell(row_index, dimensions_column_index, dm2_manual_input)
			elif line_code == 'dm3@' and dm3_manual_input:
				sheet.update_cell(row_index, dimensions_column_index, dm3_manual_input)
			elif line_code == 'dm4@' and dm4_manual_input:
				sheet.update_cell(row_index, dimensions_column_index, dm4_manual_input)
			elif line_code == 'dm5@' and dm5_manual_input:
				sheet.update_cell(row_index, dimensions_column_index, dm5_manual_input)
				
		print("Description columns updated successfully.")
		
	except Exception as e:
		print(f"Error updating description columns: {e}")
		
def update_google_sheet_with_image(line_code, image_url, include_status):
	sheet_data = fetch_data()
	for row_index, row in enumerate(sheet_data, start=2):  # Start from 2 to skip the header
		if row.get('Line Code') == line_code:
			sheet.update_cell(row_index, 11, image_url)  # Column 11 for Description
			sheet.update_cell(row_index, 5, include_status)  # Column 5 for Include
			
def fetch_internal_descriptions(data):
	"""
	This function will take the session data (selected line codes and manual inputs) and 
	return the corresponding internal descriptions from the Google Sheet.
	"""
	try:
		# Fetch the entire sheet once to avoid repeated calls
		sheet_data = fetch_data()
		description_map = {row['Line Code']: row['Internal Description'] for row in sheet_data}
		
		# Replace each line code in `data` with the corresponding internal description
		for key, line_codes in data.items():
			if isinstance(line_codes, list):
				data[key] = [description_map.get(code, code) for code in line_codes]
			else:
				data[key] = description_map.get(line_codes, line_codes)
				
		return data
	except Exception as e:
		print(f"Error fetching internal descriptions: {e}")
		return data  # In case of error, return the original data

TITLE_MAPPING = {
	'selected_special_notes': 'Special Notes',
	'selected_building_works': 'Building Works',
	'selected_boundary_lines': 'Boundary Lines',
	'selected_co': 'Contingency',
	'selected_fw': 'Finishing Works',
	'selected_foe': 'Finishing Works Optional Extras',
	'selected_ew': 'External Wall',
	'selected_er': 'Roofing Options',
	'selected_fs': 'Floor Structure',
	'selected_ps': 'Plastering',
	'selected_id': 'Internal Doors',
	'selected_dr': 'Drainage',
	'selected_wp': 'Waste and Parking',
	'selected_dw': 'Demolition Works',
	'selected_frc': 'Further Requirements and Considerations',
	'selected_ab': 'Additional Building Items',
	'selected_sww': 'Schedule of Works (Weeks 1-8)',
	'selected_tww': 'Schedule of Works (Week 9-12)',
	'selected_sd': 'Sliding Door Selection',
	'selected_sld': 'Sliding Doors',
	'selected_pc': 'Pricing Categories',
	'selected_el': 'Electrics',
	'selected_pl': 'Plumbing',
	'selected_sk': 'Skylights',
	'selected_vl': 'Velux Windows',
	'selected_ac': 'Aluminium Capping',
	'selected_gv': 'Glass Valley',
	'selected_oe': 'Optional Extras',

	# Manual input fields
	'pd1_manual_input': 'Client Address',
	'pd2_manual_input': 'Date',
	'pd3_manual_input': 'Local Council',
	'nb1_manual_input': 'Left side neighbour door number/name',
	'nb2_manual_input': 'Right side neighbour door number/name',
	'dm1_manual_input': 'Approximate extension size in metres',
	'dm2_manual_input': 'Rear depth from the original rear wall',
	'dm3_manual_input': 'Full width of wall',
	'dm4_manual_input': 'Metres width in wall side return',
	'dm5_manual_input': 'Do not use',
	'pd4_manual_input': 'Fire Rated Doors',
	'pd5_manual_input': 'Non-Fire Rated Doors',
	'cs1_manual_input': 'Local Council',
	'pd6_manual_input': 'Number of kitchen points',
	'pd7_manual_input': 'Number of kitchen lights',
	'pd8_manual_input': 'Number of loft points',
	'pd9_manual_input': 'Number of loft lights',
	'pd10_manual_input': 'Sliding Door Space',
	'an1_manual_input': 'Cellar',
	'an2_manual_input': 'Neighbours levels',
	'an3_manual_input': 'Internal to external levels (steps)',
	'an4_manual_input': 'Internal heights',
	'an5_manual_input': 'Outrigger Stories',
	'an6_manual_input': 'Flush External walls',
	'an7_manual_input': 'Further Notes'

}

# First page route
@app.route('/', methods=['POST', 'GET'], endpoint='index')
def index():
	# Store the current page in the session
	session['last_visited'] = 'index'
	
	if request.method == 'POST':
		session['pd1_manual_input'] = request.form.get('pd1_manual_input')  # Make sure this name matches the HTML field
		session['pd2_manual_input'] = request.form.get('pd2_manual_input')
		session['pd3_manual_input'] = request.form.get('pd3_manual_input')# Make sure this name matches the HTML field
		
		return redirect(url_for('page_two'))
	return render_template('form.html', first_page=True, next_page='page_two', title="Project Details")

# Second page route - Load dynamic options from Google Sheets
@app.route('/page_two', methods=['POST', 'GET'])
def page_two():
	# Get the previous page from session, default to the first page
	previous_page = session.get('last_visited', url_for('index'))
	
	# Store the current page in the session
	session['last_visited'] = 'page_two'
	
	if request.method == 'POST':
		# Store selected special notes from checkboxes into session
		selected_special_notes = request.form.getlist('selected_special_notes')  # Get selected checkboxes
		print(selected_special_notes)
		session['selected_special_notes'] = selected_special_notes
		return redirect(url_for('page_three'))
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	
	# Prepopulate based on 'Include' column
	special_notes = {}
	preselected = []
	
	# Filter the relevant rows based on cleaned prefixes (ignoring special characters)
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Identify parent prefixes by ensuring the last character is numeric
		if alphanumeric_code.startswith('sn') and alphanumeric_code[-1].isdigit():
			special_notes[line_code] = {
				'description': internal_description,
				'is_included': include == 'Y'
			}
			
		if include == 'Y':
				preselected.append(line_code)  # Add preselected if included
			
	# Send special notes to the template
	return render_template('form.html', second_page=True, previous_page=previous_page, next_page='page_three', title="Special Notes", data=special_notes, preselected=preselected)

# Third page route - Building Works
@app.route('/page_three', methods=['POST', 'GET'])
def page_three():
	# Get the previous page from session, default to 'page_two'
	previous_page = session.get('last_visited', 'page_two')
	session['last_visited'] = 'page_three'
	
	if request.method == 'POST':
		# Store selected building works from checkboxes into session
		selected_building_works = request.form.getlist('selected_building_works')  # Get selected checkboxes
		session['selected_building_works'] = selected_building_works        
		return redirect(url_for('page_four'))  # Assuming there's a next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	building_works = {}
	preselected = []
	
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Identify parent prefixes for building works
		if alphanumeric_code.startswith('bw') and alphanumeric_code[-1].isdigit():
			building_works[line_code] = {
				'description': internal_description,
				'is_included': include == 'Y'
			}
			
		if include == 'Y':
			preselected.append(line_code)
			
	# Send building works data to the template
	return render_template('form.html', third_page=True, previous_page=previous_page, next_page='page_four', title="Building Works", data=building_works, preselected=preselected)

# Fourth page route - Boundary lines

@app.route('/page_four', methods=['POST', 'GET'])
def page_four():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_three')) 
	session['last_visited'] = 'page_four'
	
	if request.method == 'POST':
		# Store selected boundary lines from checkboxes into session
		selected_boundary_lines = request.form.getlist('selected_boundary_lines')  # Get selected checkboxes
		session['selected_boundary_lines'] = selected_boundary_lines
		
		# Get manual input for nb1 and nb2
		nb1_manual_input = request.form.get('nb1_manual_input')
		nb2_manual_input = request.form.get('nb2_manual_input')
		dm1_manual_input = request.form.get('dm1_manual_input')
		dm2_manual_input = request.form.get('dm2_manual_input')
		dm3_manual_input = request.form.get('dm3_manual_input')
		dm4_manual_input = request.form.get('dm4_manual_input')

		
		# Store manual inputs into session
		session['nb1_manual_input'] = nb1_manual_input
		session['nb2_manual_input'] = nb2_manual_input
		session['dm1_manual_input'] = dm1_manual_input
		session['dm2_manual_input'] = dm2_manual_input
		session['dm3_manual_input'] = dm3_manual_input
		session['dm4_manual_input'] = dm4_manual_input

		
		return redirect(url_for('page_five'))  # Redirect to the next page (page five)
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	boundary_lines = {}
	preselected = []
	
	# Filter the relevant rows based on cleaned prefixes (ignoring special characters)
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Identify parent prefixes for boundary lines
		if alphanumeric_code.startswith(('bl', 'bs', 'cs', 'pp')) and alphanumeric_code[-1].isdigit():
			boundary_lines[line_code] = {
				'description': internal_description,
				'is_included': include == 'Y'
			}
			
		if include == 'Y':
			preselected.append(line_code)
			
	# Manually add specific 'dm' prefixed items
			if alphanumeric_code in ['dm1', 'dm2', 'dm3', 'dm4']:
				boundary_lines[line_code] = {
					'description': internal_description,
					'is_included': include == 'Y'
				}
				
			if include == 'Y':
				preselected.append(line_code)
	# Render the form
	return render_template('form.html', fourth_page=True, previous_page=previous_page, next_page='page_five', 			title="Boundary Lines & Planning Permissions", 
			data=boundary_lines, 
			preselected=preselected,
			nb1_manual_input=session.get('nb1_manual_input', ''),
			nb2_manual_input=session.get('nb2_manual_input', ''),
			dm1_manual_input=session.get('dm1_manual_input', ''),
			dm2_manual_input=session.get('dm2_manual_input', ''),
			dm3_manual_input=session.get('dm3_manual_input', ''),
			dm4_manual_input=session.get('dm4_manual_input', ''),
			)

			
# Fifth page route - External Wall (simplified version)
@app.route('/page_five', methods=['POST', 'GET'])
def page_five():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_four')) 
	session['last_visited'] = 'page_five'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_ew = request.form.getlist('selected_ew')  # Get selected checkboxes for external works
		selected_er = request.form.getlist('selected_er') 
		
		# Store the selected values into the session
		session['selected_ew'] = selected_ew
		session['selected_er'] = selected_er
		
		return redirect(url_for('page_six'))  # Assuming this is the final page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	ew_data = {}
	er_data = {}
	preselected_ew = []
	preselected_er = []	
	
	# Filter the relevant rows based on 'ew' and 'er' prefixes
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Clean the line code and process only 'ew' prefixed items
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('ew') and alphanumeric_code[-1].isdigit():
			ew_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_ew.append(line_code)
		
		# Filter for ER options
		if alphanumeric_code.startswith('er') and alphanumeric_code[-1].isdigit():
			er_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_er.append(line_code)
				
	# Render the form with ew_data and er_data
	return render_template('form.html', fifth_page=True, previous_page=previous_page, next_page='page_six', 
							title="External Wall and Roofing Options", 
							ew_data=ew_data, preselected_ew=preselected_ew,
							er_data=er_data, preselected_er=preselected_er)

	
# Sixth page route - Floor Structure (fs)
@app.route('/page_six', methods=['POST', 'GET'])
def page_six():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_five')) 
	session['last_visited'] = 'page_six'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_fs = request.form.getlist('selected_fs')  # Get selected checkboxes for floor structure
		
		# Store the selected values into the session
		session['selected_fs'] = selected_fs
		
		return redirect(url_for('page_seven'))  # Assuming this is the final page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	fs_data = {}
	preselected_fs = []
	
	# Filter the relevant rows based on 'fs' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Clean the line code and process only 'ew' prefixed items
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('fs') and alphanumeric_code[-1].isdigit():
			fs_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_fs.append(line_code)
				
	# Render the form with fs_data
	return render_template('form.html', sixth_page=True, previous_page=previous_page, next_page='page_seven', 
							title="Floor Structure", 
							fs_data=fs_data, preselected_fs=preselected_fs)
							
# Seventh page route - Plastering (ps)
@app.route('/page_seven', methods=['POST', 'GET'])
def page_seven():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_six')) 
	session['last_visited'] = 'page_seven'
	
	if request.method == 'POST':
		#Store selected checkboxes into session
		selected_ps = request.form.getlist('selected_ps')  # Get selected checkboxes for plastering
		
		# Store the selected values into the session
		session['selected_ps'] = selected_ps
		
		return redirect(url_for('page_eight'))  # Assuming this is the final page or change based on next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	ps_data = {}
	preselected_ps = []
	
	# Filter the relevant rows based on 'ps' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Clean the line code and process only 'ew' prefixed items
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('ps') and alphanumeric_code[-1].isdigit():
			ps_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_ps.append(line_code)
				
	# Render the form with ps_data
	return render_template('form.html', seventh_page=True, previous_page=previous_page, next_page='page_eight', 
														title="Plastering", 
														ps_data=ps_data, preselected_ps=preselected_ps)

# Eighth page route - Internal Doors (id)
@app.route('/page_eight', methods=['POST', 'GET'])
def page_eight():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_seven')) 
	session['last_visited'] = 'page_eight'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_id = request.form.getlist('selected_id')  # Get selected checkboxes for internal doors
		
		# Store the selected values into the session
		session['selected_id'] = selected_id
		
		# Get manual inputs for specific internal doors (e.g., id1 and id2)
		pd4_manual_input = request.form.get('pd4_manual_input')
		pd5_manual_input = request.form.get('pd5_manual_input')
		
		
		# Store manual inputs into session
		session['pd4_manual_input'] = pd4_manual_input
		session['pd5_manual_input'] = pd5_manual_input
		
		return redirect(url_for('page_nine'))  # Redirect to the final submission or next page if there is one
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	id_data = {}
	preselected_id = []
	
	# Filter the relevant rows based on 'id' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('id') and alphanumeric_code[-1].isdigit():
			id_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_id.append(line_code)
				
	# Render the form with id_data
	return render_template('form.html', eighth_page=True, previous_page=previous_page, next_page='page_nine', 
							title="Internal Doors", 
							id_data=id_data, preselected_id=preselected_id,
							pd4_manual_input=session.get('pd4_manual_input', ''),
							pd5_manual_input=session.get('pd5_manual_input', ''),
						)	

# Ninth page route - Drainage (dr)
@app.route('/page_nine', methods=['POST', 'GET'])
def page_nine():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_eight')) 
	session['last_visited'] = 'page_nine'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_dr = request.form.getlist('selected_dr')  # Get selected checkboxes for drainage
		
		# Store the selected values into the session
		session['selected_dr'] = selected_dr
		
		return redirect(url_for('page_ten'))  # Assuming there is another input page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	dr_data = {}
	preselected_dr = []
	
	# Filter the relevant rows based on 'dr' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('dr') and alphanumeric_code[-1].isdigit():
			dr_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_dr.append(line_code)
				
	# Render the form with dr_data
	return render_template('form.html', ninth_page=True, previous_page=previous_page, next_page='page_ten', 
							title="Drainage", 
							dr_data=dr_data, preselected_dr=preselected_dr)
							
# Tenth page route - Waste and Parking (wp)
@app.route('/page_ten', methods=['POST', 'GET'])
def page_ten():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_nine')) 
	session['last_visited'] = 'page_ten'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_wp = request.form.getlist('selected_wp')  # Get selected checkboxes for waste and parking
		
		# Store the selected values into the session
		session['selected_wp'] = selected_wp
		
		return redirect(url_for('page_eleven'))  # Assuming there is another input page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	wp_data = {}
	preselected_wp = []
	
	# Filter the relevant rows based on 'wp' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('wp') and alphanumeric_code[-1].isdigit():
			wp_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_wp.append(line_code)
				
	# Render the form with wp_data
	return render_template('form.html', tenth_page=True, previous_page=previous_page, next_page='page_eleven', 
							title="Waste and Parking", 
							wp_data=wp_data, preselected_wp=preselected_wp)

# Eleventh page route - Demolition Works (dw)
@app.route('/page_eleven', methods=['POST', 'GET'])
def page_eleven():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_ten')) 
	session['last_visited'] = 'page_eleven'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_dw = request.form.getlist('selected_dw')  # Get selected checkboxes for demolition works
		
		# Store the selected values into the session
		session['selected_dw'] = selected_dw
		
		return redirect(url_for('page_twelve'))  # Assuming there is another input page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	dw_data = {}
	preselected_dw = []
	
	# Filter the relevant rows based on 'dw' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('dw') and alphanumeric_code[-1].isdigit():
			dw_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_dw.append(line_code)
				
	# Render the form with dw_data
	return render_template('form.html', eleventh_page=True, previous_page=previous_page, next_page='page_twelve', 
							title="Demolition Works", 
							dw_data=dw_data, preselected_dw=preselected_dw)
							
# Twelfth page route - Further Requirements & Considerations (frc)
@app.route('/page_twelve', methods=['POST', 'GET'])
def page_twelve():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_eleven')) 
	session['last_visited'] = 'page_twelve'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_frc = request.form.getlist('selected_frc')  # Get selected checkboxes for further requirements & considerations
		
		# Store the selected values into the session
		session['selected_frc'] = selected_frc
		
		return redirect(url_for('page_thirteen'))  # Assuming there is another input page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	frc_data = {}
	preselected_frc = []
	
	# Filter the relevant rows based on 'frc' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('frc') and alphanumeric_code[-1].isdigit():
			frc_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_frc.append(line_code)
				
	# Render the form with frc_data
	return render_template('form.html', twelfth_page=True, previous_page=previous_page, next_page='page_thirteen', 
							title="Further Requirements & Considerations", 
							frc_data=frc_data, preselected_frc=preselected_frc)
							
# Thirteenth page route - Additional Building Items (ab)
@app.route('/page_thirteen', methods=['POST', 'GET'])
def page_thirteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twelve')) 
	session['last_visited'] = 'page_thirteen'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_ab = request.form.getlist('selected_ab')  # Get selected checkboxes for additional building items
		
		# Store the selected values into the session
		session['selected_ab'] = selected_ab
		
		return redirect(url_for('page_fourteen'))  # Assuming this is the final page, change if needed
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	ab_data = {}
	preselected_ab = []
	
	# Filter the relevant rows based on 'ab' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('ab') and alphanumeric_code[-1].isdigit():
			ab_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_ab.append(line_code)
				
	# Render the form with ab_data
	return render_template('form.html', thirteenth_page=True, previous_page=previous_page, next_page='page_fourteen', 
							title="Additional Building Items", 
							ab_data=ab_data, preselected_ab=preselected_ab)

# Fourteenth page route - Schedule of Works (Weeks 1-8) (sww)
@app.route('/page_fourteen', methods=['POST', 'GET'])
def page_fourteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_thirteen')) 
	session['last_visited'] = 'page_fourteen'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_sww = request.form.getlist('selected_sww')  # Get selected checkboxes for Schedule of Works (Weeks 1-8)
		
		# Store the selected values into the session
		session['selected_sww'] = selected_sww
		
		return redirect(url_for('page_fifteen'))  # Redirect to the final submission or the next page if there is one
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	sww_data = {}
	preselected_sww = []
	
	# Filter the relevant rows based on 'sww' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('sww') and alphanumeric_code[-1].isdigit():
			sww_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_sww.append(line_code)
				
	# Render the form with sww_data
	return render_template('form.html', fourteenth_page=True, previous_page=previous_page, next_page='page_fifteen', 
							title="Schedule of Works (Weeks 1-8)", 
							sww_data=sww_data, preselected_sww=preselected_sww)

# Fifteenth page route - Schedule of Works (Week 9-12) (tww)
@app.route('/page_fifteen', methods=['POST', 'GET'])
def page_fifteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_fourteen')) 
	session['last_visited'] = 'page_fifteen'
	
	if request.method == 'POST':
		# Store selected checkboxes into session
		selected_tww = request.form.getlist('selected_tww')  # Get selected checkboxes for Schedule of Works (Weeks 9-12)
		
		# Store the selected values into the session
		session['selected_tww'] = selected_tww
		
		return redirect(url_for('page_sixteen'))  # Redirect to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	tww_data = {}
	preselected_tww = []
	
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('tww') and alphanumeric_code[-1].isdigit() and line_code:
			tww_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_tww.append(line_code)
				
	# Render the form with tww_data
	return render_template('form.html', fifteenth_page=True, previous_page=previous_page, next_page='page_sixteen', 
							title="Schedule of Works (Week 9-12)", 
							tww_data=tww_data, preselected_tww=preselected_tww)
	


# Sixteenth page route - Pricing Categories (pc)
@app.route('/page_sixteen', methods=['POST', 'GET'])
def page_sixteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_fifteen')) 
	session['last_visited'] = 'page_sixteen'
	
	if request.method == 'POST':
		# Store selected pricing categories into session
		selected_pc = request.form.getlist('selected_pc')  # Get selected checkboxes for pricing categories
		session['selected_pc'] = selected_pc
		
		return redirect(url_for('page_seventeen'))  # Move to next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	pc_data = {}
	preselected_pc = []
	
	# Filter the relevant rows based on 'pc' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('pc') and alphanumeric_code[-1].isdigit():
			pc_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_pc.append(line_code)
				
	# Render the form with pc_data
	return render_template('form.html', sixteenth_page=True, previous_page=previous_page, next_page='page_seventeen', 
							title="Pricing Categories", 
							pc_data=pc_data, preselected_pc=preselected_pc)
							
							
# Seventeenth page route - Electrics (el) - Only shown if pc4 is selected
@app.route('/page_seventeen', methods=['POST', 'GET'])
def page_seventeen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_sixteen')) 
	session['last_visited'] = 'page_seventeen'
	
	if request.method == 'POST':
		# Collect manual input values for electrics
		session['pd6_manual_input'] = request.form.get('pd6_manual_input')
		session['pd7_manual_input'] = request.form.get('pd7_manual_input')
		session['pd8_manual_input'] = request.form.get('pd8_manual_input')
		session['pd9_manual_input'] = request.form.get('pd9_manual_input')
		
		# Store selected electrics checkboxes into session
		selected_el = request.form.getlist('selected_el')  # Get selected checkboxes for electrics
		session['selected_el'] = selected_el  # Store them in session
		
		return redirect(url_for('page_eighteen'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	el_data = {}
	preselected_el = []
	
	# Filter the relevant rows based on 'el' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('el') and alphanumeric_code[-1].isdigit():
			el_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_el.append(line_code)
				
	# Render the form with el_data
	return render_template('form.html', seventeenth_page=True, previous_page=previous_page, next_page='page_eighteen', 
							title="Electrics", 
							el_data=el_data, preselected_el=preselected_el,
							pd6_manual_input=session.get('pd6_manual_input', ''),
							pd7_manual_input=session.get('pd7_manual_input', ''),
							pd8_manual_input=session.get('pd8_manual_input', ''),
							pd9_manual_input=session.get('pd9_manual_input', ''),
						)							
							

# Eighteenth page route - Plumbing (pl)
@app.route('/page_eighteen', methods=['POST', 'GET'])
def page_eighteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_seventeen')) 
	session['last_visited'] = 'page_eighteen'
	
	if request.method == 'POST':
		# Store selected plumbing options into session
		selected_pl = request.form.getlist('selected_pl')  # Get selected checkboxes for plumbing
		
		# Store the selected values into the session
		session['selected_pl'] = selected_pl
		
		return redirect(url_for('page_nineteen'))  # Replace 'next_page' with the actual next page route
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	pl_data = {}
	preselected_pl = []
	
	# Filter the relevant rows based on 'pl' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('pl') and alphanumeric_code[-1].isdigit():
			pl_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_pl.append(line_code)
				
	# Render the form with pl_data
	return render_template('form.html', eighteenth_page=True, previous_page=previous_page, next_page='page_nineteen', 
							title="Plumbing", 
							pl_data=pl_data, preselected_pl=preselected_pl)
							
# Nineteenth page route - Skylights (sk)
@app.route('/page_nineteen', methods=['POST', 'GET'])
def page_nineteen():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_eighteen')) 
	session['last_visited'] = 'page_nineteen'
	
	if request.method == 'POST':
		# Store selected skylights options into session
		selected_sk = request.form.getlist('selected_sk')  # Get selected checkboxes for skylights
		session['selected_sk'] = selected_sk  # Store the selected values into the session
		
		return redirect(url_for('page_twenty'))  # Go to the next page (page twenty)
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	sk_data = {}
	preselected_sk = []
	
	# Filter the relevant rows based on 'sk' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('sk') and alphanumeric_code[-1].isdigit():
			sk_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_sk.append(line_code)
				
	# Render the form with sk_data
	return render_template('form.html', nineteenth_page=True, previous_page=previous_page, next_page='page_twenty',      title="Skylights", 
			sk_data=sk_data, preselected_sk=preselected_sk)

# Twentieth page route - Velux Windows (vl) - Only shown if pc7 is selected
@app.route('/page_twenty', methods=['POST', 'GET'])
def page_twenty():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_nineteen')) 
	session['last_visited'] = 'page_twenty'
	
	if request.method == 'POST':
		# Store selected velux windows options into session
		selected_vl = request.form.getlist('selected_vl')  # Get selected checkboxes for velux windows
		session['selected_vl'] = selected_vl
		
		return redirect(url_for('page_twenty_one'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	vl_data = {}
	preselected_vl = []
	
	# Filter the relevant rows based on 'vl' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('vl') and alphanumeric_code[-1].isdigit():
			vl_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_vl.append(line_code)
				
	# Render the form with vl_data
	return render_template('form.html', twentieth_page=True, previous_page=previous_page, next_page='page_twenty_one', 
							title="Velux Windows", 
							vl_data=vl_data, preselected_vl=preselected_vl)

# Twenty-first page route - Aluminium Capping (ac) - Only shown if pc8 is selected
@app.route('/page_twenty_one', methods=['POST', 'GET'])
def page_twenty_one():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty')) 
	session['last_visited'] = 'page_twenty_one'
	
	if request.method == 'POST':
		# Store selected aluminium capping options into session
		selected_ac = request.form.getlist('selected_ac')  # Get selected checkboxes for aluminium capping
		previous_page = session.get('last_visited', url_for('index')) 
		session['selected_ac'] = selected_ac
		return redirect(url_for('page_twenty_two'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	ac_data = {}
	preselected_ac = []
	
	# Filter the relevant rows based on 'ac' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('ac') and alphanumeric_code[-1].isdigit():
			ac_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_ac.append(line_code)
				
	# Render the form with ac_data
	return render_template('form.html', twenty_first_page=True, previous_page=previous_page, next_page='page_twenty_two', 
							title="Aluminium Capping", 
							ac_data=ac_data, preselected_ac=preselected_ac)
							

# Twenty-second page route - Glass Valley (gv)
@app.route('/page_twenty_two', methods=['POST', 'GET'])
def page_twenty_two():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_one')) 
	session['last_visited'] = 'page_twenty_two'
	
	if request.method == 'POST':
		# Store selected glass valley options into session
		previous_page = session.get('last_visited', url_for('index')) 
		selected_gv = request.form.getlist('selected_gv')  # Get selected checkboxes for glass valley
		session['selected_gv'] = selected_gv
		return redirect(url_for('page_twenty_three'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	gv_data = {}
	preselected_gv = []
	
	# Filter the relevant rows based on 'gv' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('gv') and alphanumeric_code[-1].isdigit():
			gv_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_gv.append(line_code)
				
	# Render the form with gv_data
	return render_template('form.html', twenty_second_page=True, previous_page=previous_page, next_page='page_twenty_three', 
							title="Glass Valley", 
							gv_data=gv_data, preselected_gv=preselected_gv)
							

# Twenty-third page route - Sliding Doors (sld, sd)
@app.route('/page_twenty_three', methods=['POST', 'GET'])
def page_twenty_three():
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_two')) 
	session['last_visited'] = 'page_twenty_three'
	
	if request.method == 'POST':
		# Store selected checkboxes for sld
		selected_sld = request.form.getlist('selected_sld')
		session['selected_sld'] = selected_sld
		
		# Get manual input for pd10
		pd10_manual_input = request.form.get('pd10_manual_input')
		session['pd10_manual_input'] = pd10_manual_input
		
		# Store selected option from the dropdown for sd
		selected_sd = request.form.get('selected_sd')
		session['selected_sd'] = selected_sd
		
		return redirect(url_for('page_twenty_four'))  # Move to the review page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	sld_data = {}
	preselected_sld = []
	sd_options = []
	pd10_label = ''
	
	# Filter the relevant rows based on cleaned prefixes (ignoring special characters)
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Handle 'sld' prefix for checkboxes
		if alphanumeric_code.startswith('sld') and len(alphanumeric_code) > 1 and alphanumeric_code[-1].isdigit():
			sld_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_sld.append(line_code)
				
		# Find the label for pd10 (from the description column)
		if line_code == 'pd10':
			pd10_label = internal_description
			
		# Handle 'sd' prefix for dropdown options
		if alphanumeric_code.startswith('sd') and len(alphanumeric_code) > 1 and alphanumeric_code[-1].isdigit():
			sd_options.append({'line_code': line_code, 'description': internal_description})
			
	# Render the form with the necessary data
	return render_template(
		'form.html',
		twenty_third_page=True,
		previous_page=previous_page,
		next_page='page_twenty_four',
		title="Sliding Doors",
		pd10_label=pd10_label,
		sld_data=sld_data,
		preselected_sld=preselected_sld,
		sd_options=sd_options,
		pd10_manual_input=session.get('pd10_manual_input', '')
	)
	
# Twenty-fourth page route - Optional Extras
@app.route('/page_twenty_four', methods=['POST', 'GET'])
def page_twenty_four():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_three')) 
	session['last_visited'] = 'page_twenty_four'
	
	if request.method == 'POST':
		# Store selected optional extras options into session
		selected_oe = request.form.getlist('selected_oe')  # Get selected checkboxes for glass valley
		session['selected_oe'] = selected_oe
		return redirect(url_for('page_twenty_five'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	oe_data = {}
	preselected_oe = []
	
	# Filter the relevant rows based on 'gv' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('oe') and alphanumeric_code[-1].isdigit():
			oe_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_oe.append(line_code)
				
	# Render the form with gv_data
	return render_template('form.html', twenty_fourth_page=True, previous_page=previous_page, next_page='page_twenty_five', 
							title="Optional Extras", 
							oe_data=oe_data, preselected_oe=preselected_oe)

# Twenty-fifth page route - Finsihing Works
@app.route('/page_twenty_five', methods=['POST', 'GET'])
def page_twenty_five():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_four')) 
	session['last_visited'] = 'page_twenty_five'
	
	if request.method == 'POST':
		# Store selected optional extras options into session
		selected_fw = request.form.getlist('selected_fw')  # Get selected checkboxes for glass valley
		session['selected_fw'] = selected_fw
		return redirect(url_for('page_twenty_six'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	fw_data = {}
	preselected_fw = []
	
	# Filter the relevant rows based on 'gv' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('fw') and alphanumeric_code[-1].isdigit():
			fw_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_fw.append(line_code)
				
	# Render the form with fw_data
	return render_template('form.html', twenty_fifth_page=True, previous_page=previous_page, next_page='page_twenty_six', 
							title="Finishing Works", 
							fw_data=fw_data, preselected_fw=preselected_fw)
							
# Twenty-sixth page route - Contingency
@app.route('/page_twenty_six', methods=['POST', 'GET'])
def page_twenty_six():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_five')) 
	session['last_visited'] = 'page_twenty_six'
	
	if request.method == 'POST':
		# Store selected optional extras options into session
		selected_co = request.form.getlist('selected_co')  # Get selected checkboxes for Contingency
		session['selected_co'] = selected_co
		return redirect(url_for('page_twenty_seven'))  # Go to the next page

	# Load data from Google Sheets
	sheet_data = fetch_data()
	co_data = {}
	preselected_co = []
	
	# Filter the relevant rows based on 'co' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('co') and alphanumeric_code[-1].isdigit() and not alphanumeric_code.startswith('com'):
			co_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_co.append(line_code)
				
	# Render the form with co_data
	return render_template('form.html', twenty_sixth_page=True, previous_page=previous_page, next_page='page_twenty_seven', 
							title="Contingency", 
							co_data=co_data, preselected_co=preselected_co)
							
# Twenty-Seventh page route - Finishing Works Optional Extras
@app.route('/page_twenty_seven', methods=['POST', 'GET'])
def page_twenty_seven():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_six')) 
	session['last_visited'] = 'page_twenty_seven'
	
	if request.method == 'POST':
		# Store selected optional extras options into session
		selected_foe = request.form.getlist('selected_foe')  # Get selected checkboxes for Finishing Works Optional Extras
		session['selected_foe'] = selected_foe
		return redirect(url_for('page_twenty_eight'))  # Go to the next page
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	foe_data = {}
	preselected_foe = []
	
	# Filter the relevant rows based on 'foe' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		# Convert the line code to alphanumeric using the helper function
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('foe') and alphanumeric_code[-1].isdigit():
			foe_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
			if include == 'Y':
				preselected_foe.append(line_code)
				
	# Render the form with foe_data
	return render_template('form.html', twenty_seventh_page=True, previous_page=previous_page, next_page='page_twenty_eight', 
							title="Finishing Works Optional Extras", 
							foe_data=foe_data, preselected_foe=preselected_foe)


# Twenty-Eighth page route - Additional Notes
@app.route('/page_twenty_eight', methods=['POST', 'GET'])
def page_twenty_eight():
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('page_twenty_seven')) 
	session['last_visited'] = 'page_twenty_eight'
	
	if request.method == 'POST':
		# Collect each additional note input from the form
		session['an1_manual_input'] = request.form.get('an1_manual_input')
		session['an2_manual_input'] = request.form.get('an2_manual_input')
		session['an3_manual_input'] = request.form.get('an3_manual_input')
		session['an4_manual_input'] = request.form.get('an4_manual_input')
		session['an5_manual_input'] = request.form.get('an5_manual_input')
		session['an6_manual_input'] = request.form.get('an6_manual_input')
		session['an7_manual_input'] = request.form.get('an7_manual_input')
		
		# Redirect to the review page after submitting additional notes
		return redirect(url_for('page_twenty_nine'))
	
	# Render the form for additional notes input
	return render_template(
		'form.html',
		twenty_eighth_page=True,
		previous_page=previous_page,
		next_page='page_twenty_nine',
		title="Additional Notes",
		an1_manual_input=session.get('an1_manual_input', ''),
		an2_manual_input=session.get('an2_manual_input', ''),
		an3_manual_input=session.get('an3_manual_input', ''),
		an4_manual_input=session.get('an4_manual_input', ''),
		an5_manual_input=session.get('an5_manual_input', ''),
		an6_manual_input=session.get('an6_manual_input', ''),
		an7_manual_input=session.get('an7_manual_input', '')
	)
	

# Twenty-Ninth page route - Image Upload
@app.route('/page_twenty_nine', methods=['POST', 'GET'])
def page_twenty_nine():
	# Track previous page for navigation
	previous_page = session.get('last_visited', url_for('page_twenty_eight'))
	session['last_visited'] = 'page_twenty_nine'
	
	if request.method == 'POST':
		# Define image fields to upload based on expected line codes
		image_fields = ['img1', 'img2', 'img3'] + [f'img{i}' for i in range(23, 33)]
		for field in image_fields:
			file = request.files.get(field)
			if file and allowed_file(file.filename):
				filename = secure_filename(file.filename)
				file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
				image_url = url_for('static', filename=f'uploads/{filename}', _external=True)
				
				# Save each image URL to the session for display on the review page
				session[field] = f'uploads/{filename}'
				
				# Update Google Sheet with image URL and mark "Include" as 'Y'
				update_google_sheet_with_image(field, image_url, 'Y')
			else:
				# If no image is uploaded, mark "Include" as 'N' in the Google Sheet
				update_google_sheet_with_image(field, '', 'N')
				
		# Redirect to review page after handling all images
		return redirect(url_for('review'))
	
	# Send data to form.html with specific page identifier for image uploads
	return render_template('form.html', twenty_ninth_page=True, previous_page=previous_page, next_page='review', title="Upload Images")



# Review Page 						 
@app.route('/review', methods=['GET', 'POST'])
def review():
	if request.method == 'POST':
		return redirect(url_for('review'))
	
	# Fetch all session data to display on the review page
	review_data = {
		'selected_special_notes': session.get('selected_special_notes'),
		'selected_building_works': session.get('selected_building_works'),
		'selected_boundary_lines': session.get('selected_boundary_lines'),
		'selected_co': session.get('selected_co'),
		'selected_fw': session.get('selected_fw'),
		'selected_foe': session.get('selected_foe'),
		'selected_ew': session.get('selected_ew'),
		'selected_er': session.get('selected_er'),
		'selected_fs': session.get('selected_fs'),
		'selected_ps': session.get('selected_ps'),
		'selected_id': session.get('selected_id'),
		'selected_dr': session.get('selected_dr'),
		'selected_wp': session.get('selected_wp'),
		'selected_dw': session.get('selected_dw'),
		'selected_frc': session.get('selected_frc'),
		'selected_ab': session.get('selected_ab'),
		'selected_sww': session.get('selected_sww'),
		'selected_tww': session.get('selected_tww'),
		'selected_pc': session.get('selected_pc'),
		'selected_el': session.get('selected_el'),
		'selected_pl': session.get('selected_pl'),
		'selected_sk': session.get('selected_sk'),
		'selected_vl': session.get('selected_vl'),
		'selected_ac': session.get('selected_ac'),
		'selected_gv': session.get('selected_gv'),
		'selected_sld': session.get('selected_sld'),
		'selected_sd': session.get('selected_sd'),
		'selected_oe': session.get('selected_oe'),
		
		# Manual inputs
		'pd1_manual_input': session.get('pd1_manual_input'),
		'pd2_manual_input': session.get('pd2_manual_input'),
		'pd3_manual_input': session.get('pd3_manual_input'),
		'nb1_manual_input': session.get('nb1_manual_input'),
		'nb2_manual_input': session.get('nb2_manual_input'),
		'pd4_manual_input': session.get('pd4_manual_input'),
		'pd5_manual_input': session.get('pd5_manual_input'),
		'pd6_manual_input': session.get('pd6_manual_input'),
		'pd7_manual_input': session.get('pd7_manual_input'),
		'pd8_manual_input': session.get('pd8_manual_input'),
		'pd9_manual_input': session.get('pd9_manual_input'),
		'pd10_manual_input': session.get('pd10_manual_input'),
		'an1_manual_input': session.get('an1_manual_input'),
		'an2_manual_input': session.get('an2_manual_input'),
		'an3_manual_input': session.get('an3_manual_input'),
		'an4_manual_input': session.get('an4_manual_input'),
		'an5_manual_input': session.get('an5_manual_input'),
		'an6_manual_input': session.get('an6_manual_input'),
		'an7_manual_input': session.get('an7_manual_input'),
		'dm1_manual_input': session.get('dm1_manual_input'),
		'dm2_manual_input': session.get('dm2_manual_input'),
		'dm3_manual_input': session.get('dm3_manual_input'),
		'dm4_manual_input': session.get('dm4_manual_input'),

	}
	
	# Map image session keys to their filenames for preview
	uploaded_images = {
		'Cover Image': session.get('img1'),
		'Building Works cgi': session.get('img2'),
		'Floorplan': session.get('img3'),
		'Site Image 1': session.get('img23'),
		'Site Image 2': session.get('img24'),
		'Site Image 3': session.get('img25'),
		'Site Image 4': session.get('img26'),
		'Site Image 5': session.get('img27'),
		'Site Image 6': session.get('img28'),
		'Site Image 7': session.get('img29'),
		'Site Image 8': session.get('img30'),
		'Site Image 9': session.get('img31'),
		'Site Image 10': session.get('img32'),
		# Add further images up to img32 if necessary
	}
	
	# Fetch internal descriptions for selected items
	internal_descriptions = fetch_internal_descriptions(review_data)  # Ensure transformation here
		
	# Create a dictionary with readable titles
	review_with_titles = {TITLE_MAPPING.get(key, key): value for key, value in internal_descriptions.items()}
	
	# Pass TITLE_MAPPING and other data to the template
	return render_template('review.html', review_page=True, review_data=review_with_titles, TITLE_MAPPING=TITLE_MAPPING, current_page='review', title="Review Page")

# Submit route
@app.route('/submit', methods=['GET', 'POST'])
def submit():
	if request.method == 'POST':
		print("Form data received: ", request.form)
		try:
			
			# Only include session data that is related to prefixes (checkboxes), not manual inputs
			checkbox_keys = ['selected_special_notes', 'selected_building_works', 'selected_boundary_lines',
				'selected_co', 'selected_fw', 'selected_foe', 'selected_ew', 'selected_er', 'selected_fs',
				'selected_ps', 'selected_id', 'selected_dr', 'selected_wp', 'selected_dw',
				'selected_frc', 'selected_ab', 'selected_sww', 'selected_tww', 'selected_pc',
				'selected_el', 'selected_pl', 'selected_sk', 'selected_vl', 'selected_ac',
				'selected_gv', 'selected_sld', 'selected_sd', 'selected_oe']  # Extend this list to include only checkbox fields
			
			combined_data = []
			for key in checkbox_keys:
				combined_data += session.get(key, [])
			
			print(f"Combined data (selected prefixes) for update_include_column: {combined_data}")
			
			# Perform the batch update for prefixes (checkbox selections)
			if combined_data:
				print("Calling update_include_column with combined_data: ", combined_data)
				update_include_column(combined_data)   # Only update checkboxes
			
			manual_inputs = {
				'pd1_manual_input': session.get('pd1_manual_input'),  
				'pd2_manual_input': session.get('pd2_manual_input'),
				'pd3_manual_input': session.get('pd3_manual_input'),
				'pd4_manual_input': session.get('pd4_manual_input'),
				'pd5_manual_input': session.get('pd5_manual_input'),
				'pd6_manual_input': session.get('pd6_manual_input'),
				'pd7_manual_input': session.get('pd7_manual_input'),
				'pd8_manual_input': session.get('pd8_manual_input'),
				'pd9_manual_input': session.get('pd9_manual_input'),
				'pd10_manual_input': session.get('pd10_manual_input'),
				'nb1_manual_input': session.get('nb1_manual_input'),
				'nb2_manual_input': session.get('nb2_manual_input'),
				'an1_manual_input': session.get('an1_manual_input'),
				'an2_manual_input': session.get('an2_manual_input'),
				'an3_manual_input': session.get('an3_manual_input'),
				'an4_manual_input': session.get('an4_manual_input'),
				'an5_manual_input': session.get('an5_manual_input'),
				'an6_manual_input': session.get('an6_manual_input'),
				'an7_manual_input': session.get('an7_manual_input'),
				'dm1_manual_input': session.get('dm1_manual_input'),
				'dm2_manual_input': session.get('dm2_manual_input'),
				'dm3_manual_input': session.get('dm3_manual_input'),
				'dm4_manual_input': session.get('dm4_manual_input'),
				'dm5_manual_input': session.get('dm5_manual_input'),
			}
			print("Manual inputs received: ", manual_inputs)
			
			# Update the placeholders in the Google Sheet for address, date, and manual inputs
			print("Updating description with: ", manual_inputs)
			update_description_column(
				manual_inputs['pd1_manual_input'], 
				manual_inputs['pd2_manual_input'],
				manual_inputs['pd3_manual_input'],
				manual_inputs['pd4_manual_input'],
				manual_inputs['pd5_manual_input'],
				manual_inputs['pd6_manual_input'],
				manual_inputs['pd7_manual_input'],
				manual_inputs['pd8_manual_input'],
				manual_inputs['pd9_manual_input'],
				manual_inputs['pd10_manual_input'],
				manual_inputs['nb1_manual_input'], 
				manual_inputs['nb2_manual_input'], 
				manual_inputs['an1_manual_input'], 
				manual_inputs['an2_manual_input'], 
				manual_inputs['an3_manual_input'], 
				manual_inputs['an4_manual_input'], 
				manual_inputs['an5_manual_input'], 
				manual_inputs['an6_manual_input'], 
				manual_inputs['an7_manual_input'], 
				manual_inputs['dm1_manual_input'], 
				manual_inputs['dm2_manual_input'], 
				manual_inputs['dm3_manual_input'], 
				manual_inputs['dm4_manual_input'],
				manual_inputs['dm5_manual_input'], 
			)
			
			# Return a success message or redirect to a new page
			return jsonify({'status': 'success', 'message': 'Data successfully updated!'})
				
		except Exception as e:
			print(f"Error during submission: {str(e)}")
			return jsonify({'status': 'error', 'message': str(e)}), 500
		

# Route for the production page (trigger production script)
@app.route('/production-page')
def trigger_production_page():
	return render_template('production.html')


# Trigger production script when button clicked
@app.route('/trigger_production')
def trigger_production():
	try:
		script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'QM_Production.py')
		result = subprocess.run(['python3', script_path], capture_output=True, text=True)
		
		if result.returncode == 0:
			output = result.stdout.strip()
			if "Document link:" in output:
				document_url = output.split("Document link: ")[-1].strip()
			else:
				document_url = "No valid document link found."
				
			# Return the button with document URL
			if document_url:
				return f"""
				<h2>Your document is ready!</h2>
				<p>
					<a href="{document_url}" target="_blank" class="btn">Click here to open it in a new tab</a>
				</p>
				"""
			else:
				return "No valid document link found.", 500
			
		else:
			return f"Error in production script: {result.stderr}", 500
		
	except Exception as e:
		return f"Error: {e}", 500
	
if __name__ == '__main__':
	app.run(debug=True)
	
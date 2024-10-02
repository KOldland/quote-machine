from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import gspread
import subprocess
from google.oauth2.service_account import Credentials
import re
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

# Set a secret key for session management
app.secret_key = 'S)x;:qtD5EC"'

# Set up server-side session
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
app.config['SESSION_FILE_DIR'] = './flask_session/'  # Create a directory for sessions
app.config['SECRET_KEY'] = 'S)x;:qtD5EC"'

# Initialize the session extension
Session(app)

# Set up Google Sheets API credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('QM_credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet_id = '1gscALSOGoaEYyuUN0zyu_pRAMvjjJvWjv3ZnAFCd5rQ'
sheet = client.open_by_key(spreadsheet_id).sheet1

TITLE_MAPPING = {
    'selected_special_notes': 'Special Notes',
    'selected_building_works': 'Building Works',
    'selected_boundary_lines': 'Boundary Lines',
    'selected_co': 'Contingency',
    'selected_fw': 'Finishing Works',
    'selected_fwoe': 'Finishing Works Optional Extras',
    'selected_ew': 'External Works',
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
    'selected_pc': 'Pricing Categories',
    'selected_el': 'Electrics',
    'selected_pl': 'Plumbing',
    'selected_sl': 'Skylights',
    'selected_vl': 'Velux Windows',
    'selected_ac': 'Aluminium Capping',
    'selected_gv': 'Glass Valley',
    'selected_sds': 'Sliding Doors Selections',
    'selected_sd': 'Selected Dropdown Option for Sliding Doors',
    
    # Manual input fields
    'nb1_manual_input': 'Left side neighbour door number/name',
    'nb2_manual_input': 'Right side neighbour door number/name',
    'dm1_manual_input': 'Approximate extension size in metres',
    'dm2_manual_input': 'Rear depth from the original rear wall',
    'dm3_manual_input': 'Full width of wall',
    'dm4_manual_input': 'Metres width in wall side return',
    'dm5_manual_input': 'Special Dimension (dm5)',
    'cs1_manual_input': 'Local Council',
    'an1_manual_input': 'Cellar',
    'an2_manual_input': 'Neighbours levels',
    'an3_manual_input': 'Internal to external levels (steps)',
    'an4_manual_input': 'Internal heights',
    'an5_manual_input': 'Outrigger Stories',
    'an6_manual_input': 'Flush External walls',
    'an7_manual_input': 'Further Notes'
}


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

# Helper function to remove special characters from line codes
def clean_line_code(line_code):
    return re.sub(r'[^\w]', '', line_code)  # Removes non-alphanumeric characters

# Function to update 'Include' column based on selected parent and child prefixes using batch updates
def update_include_column(selected_prefixes):
    
    try:
        sheet_data = fetch_data()
        updates = []  # Collect all updates here
        
        for row_index, row in enumerate(sheet_data, start=2):  # Start from 2 because row 1 is the header
            line_code = row.get('Line Code', '')
            clean_code = clean_line_code(line_code)  # Clean the line code for comparison
        
            # If the cleaned line code starts with any of the selected prefixes, mark it as 'Y'
            include_value = 'Y' if any(clean_code.startswith(prefix) for prefix in selected_prefixes) else ''
        
            if include_value == 'Y':
                updates.append({
                   'range': f'Include!E{row_index}',  # Column E = include column
                   'values': [[include_value]]
                    })            
    # Send all updates in a batch
        if updates:
            sheet.batch_update(updates)
            
    except Exception as e:
        print(f"Error updating include column: {e}")
    
# Function to update the 'Description' column and "unit Column"
def update_description_column(address, date, nb1_manual_input=None, nb2_manual_input=None, 
                    dm1_manual_input=None, dm2_manual_input=None, dm3_manual_input=None, 
                    dm4_manual_input=None, dm5_manual_input=None, cs1_manual_input=None,
                    an1_manual_input=None, an2_manual_input=None, an3_manual_input=None,
                    an4_manual_input=None, an5_manual_input=None, an6_manual_input=None,
                    an7_manual_input=None, id1_manual_input=None, id2_manual_input=None):
    try:
        # Fetch the sheet data
        sheet_data = fetch_data()
        
        description_column_index = 11  # Description column (column 11)
        dimensions_column_index = 10  # Dimensions column (column 10)
        unit_input_column_index = 7  # Units column (column 7)
        
        # Iterate over the rows and look for the placeholders in the "Line Code" column
        for row_index, row in enumerate(sheet_data, start=2):  # Start from 2 to skip the header
            line_code = row.get('Line Code', '')
        
        # Update the placeholders accordingly in the correct columns
        if line_code == 'cd1@':
            sheet.update_cell(row_index, description_column_index, address)
        elif line_code == 'todays_date@':
            sheet.update_cell(row_index, description_column_index, date)
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
        elif line_code == 'cs1#' and cs1_manual_input:
            sheet.update_cell(row_index, description_column_index, cs1_manual_input)
        elif line_code == 'el1' and el1_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, el1_manual_input)
        elif line_code == 'el2' and el2_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, el2_manual_input)
        elif line_code == 'el3' and el3_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, el3_manual_input)
        elif line_code == 'el4' and el4_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, el4_manual_input)
        elif line_code == 'id2^' and id1_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, id1_manual_input)
        elif line_code == 'id3^' and id2_manual_input:
            sheet.update_cell(row_index, unit_input_column_index, id2_manual_input)
        # Additional Notes Manual Input
        elif line_code == 'an1#' and an1_manual_input:
            sheet.update_cell(row_index, description_column_index, an1_manual_input)
        elif line_code == 'an2#' and an2_manual_input:
            sheet.update_cell(row_index, description_column_index, an2_manual_input)
        elif line_code == 'an3#' and an3_manual_input:
            sheet.update_cell(row_index, description_column_index, an3_manual_input)
        elif line_code == 'an4#' and an4_manual_input:
            sheet.update_cell(row_index, description_column_index, an4_manual_input)
        elif line_code == 'an5#' and an5_manual_input:
            sheet.update_cell(row_index, description_column_index, an5_manual_input)
        elif line_code == 'an6#' and an6_manual_input:
            sheet.update_cell(row_index, description_column_index, an6_manual_input)
        elif line_code == 'an7#' and an7_manual_input:
            sheet.update_cell(row_index, description_column_index, an7_manual_input)
                        
    except Exception as e:
        print(f"Error updating description column: {e}")
        
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
    
    
            
# First page route
@app.route('/', methods=['POST', 'GET'], endpoint='index')
def index():
    
    # Store the current page in the session
    session['last_visited'] = 'index'
    
    if request.method == 'POST':
        session['address'] = request.form.get('address')
        session['date'] = request.form.get('date')
        return redirect(url_for('page_two'))
    return render_template('index.html', first_page=True, next_page='page_two', title="Project Details")

# Second page route - Load dynamic options from Google Sheets
@app.route('/page-two', methods=['POST', 'GET'])
def page_two():
    # Get the previous page from session, default to the first page
    previous_page = session.get('last_visited', url_for('index'))
    
    # Store the current page in the session
    session['last_visited'] = 'page_two'
    
    if request.method == 'POST':
        # Store selected special notes from checkboxes into session
        selected_special_notes = request.form.getlist('special_notes')  # Get selected checkboxes
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
        
        # Clean the line code by removing special characters like #, @, etc.
        clean_code = clean_line_code(line_code)
        
        # Identify parent prefixes by ensuring the last character is numeric
        if clean_code.startswith('sn') and clean_code[-1].isdigit():
            special_notes[line_code] = {
                'description': internal_description,
                'is_included': include == 'Y'
            }
            
        if include == 'Y':
                preselected.append(line_code)  # Add preselected if included
            
    # Send special notes to the template
    return render_template('index.html', second_page=True, previous_page=previous_page, next_page='page_three', title="Special Notes", data=special_notes, preselected=preselected)


# Third page route - Building Works
@app.route('/page-three', methods=['POST', 'GET'])
def page_three():
    # Get the previous page from session, default to 'page_two'
    previous_page = session.get('last_visited', 'page_two')
    
    # Store the current page in the session
    session['last_visited'] = 'page_three'
    
    if request.method == 'POST':
        # Store selected building works from checkboxes into session
        selected_building_works = request.form.getlist('building_works')  # Get selected checkboxes
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
        # Clean the line code by removing special characters like #, @, etc.
        clean_code = clean_line_code(line_code)
        
        # Identify parent prefixes for building works
        if clean_code.startswith('bw') and clean_code[-1].isdigit():
            building_works[line_code] = {
                'description': internal_description,
                'is_included': include == 'Y'
            }
            
        if include == 'Y':
            preselected.append(line_code)
            
    # Send building works data to the template
    return render_template('index.html', third_page=True, previous_page=previous_page, next_page='page_four', title="Building Works", data=building_works, preselected=preselected)

# Fourth page route - Boundary lines

@app.route('/page-four', methods=['POST', 'GET'])
def page_four():
    
    # Store the current page in the session
    session['last_visited'] = 'page_four'
    
    if request.method == 'POST':
        # Store selected boundary lines from checkboxes into session
        selected_boundary_lines = request.form.getlist('boundary_lines')  # Get selected checkboxes
        session['selected_boundary_lines'] = selected_boundary_lines
        
        # Get manual input for nb1 and nb2
        nb1_manual_input = request.form.get('nb1_manual_input')
        nb2_manual_input = request.form.get('nb2_manual_input')
        dm1_manual_input = request.form.get('dm1_manual_input')
        dm2_manual_input = request.form.get('dm2_manual_input')
        dm3_manual_input = request.form.get('dm3_manual_input')
        dm4_manual_input = request.form.get('dm4_manual_input')
        cs1_manual_input = request.form.get('cs1_manual_input')
        
        # Store manual inputs into session
        session['nb1_manual_input'] = nb1_manual_input
        session['nb2_manual_input'] = nb2_manual_input
        session['dm1_manual_input'] = dm1_manual_input
        session['dm2_manual_input'] = dm2_manual_input
        session['dm3_manual_input'] = dm3_manual_input
        session['dm4_manual_input'] = dm4_manual_input
        session['cs1_manual_input'] = cs1_manual_input
        
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
        
        # Clean the line code by removing special characters like #, @, etc.
        clean_code = clean_line_code(line_code)
        
        # Identify parent prefixes for boundary lines
        if clean_code.startswith(('bl', 'bs', 'cs', 'pp')) and clean_code[-1].isdigit():
            boundary_lines[line_code] = {
                'description': internal_description,
                'is_included': include == 'Y'
            }
            
        if include == 'Y':
            preselected.append(line_code)
            
    # Manually add specific 'dm' prefixed items
            if clean_code in ['dm1', 'dm2', 'dm3', 'dm4']:
                boundary_lines[line_code] = {
                    'description': internal_description,
                    'is_included': include == 'Y'
                }
                
            if include == 'Y':
                preselected.append(line_code)
    # Render the form
    return render_template('index.html', fourth_page=True, previous_page='page_three', next_page='page_five', 
            title="Boundary Lines & Planning Permissions", 
            data=boundary_lines, 
            preselected=preselected,
            nb1_manual_input=session.get('nb1_manual_input', ''),
            nb2_manual_input=session.get('nb2_manual_input', ''),
            dm1_manual_input=session.get('dm1_manual_input', ''),
            dm2_manual_input=session.get('dm2_manual_input', ''),
            dm3_manual_input=session.get('dm3_manual_input', ''),
            dm4_manual_input=session.get('dm4_manual_input', ''),
            cs1_manual_input=session.get('cs1_manual_input', ''))        
            
# Fifth page route - External Works (simplified version)
@app.route('/page-five', methods=['POST', 'GET'])
def page_five():
    
    # Store the current page in the session
    session['last_visited'] = 'page_five'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_ew = request.form.getlist('ew')  # Get selected checkboxes for external works
        
        # Store the selected values into the session
        session['selected_ew'] = selected_ew
        
        return redirect(url_for('page_six'))  # Assuming this is the final page
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    ew_data = {}
    preselected_ew = []
    
    # Filter the relevant rows based on 'ew' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'ew' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('ew') and clean_code[-1].isdigit():
            ew_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_ew.append(line_code)
                
    # Render the form with ew_data
    return render_template('index.html', fifth_page=True, previous_page='page_four', next_page='submit', 
                           title="External Wall", 
                           ew_data=ew_data, preselected_ew=preselected_ew)

# Sixth page route - Floor Structure (fs)
@app.route('/page-six', methods=['POST', 'GET'])
def page_six():
    
    # Store the current page in the session
    session['last_visited'] = 'page_six'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_fs = request.form.getlist('fs')  # Get selected checkboxes for floor structure
        
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
        
        # Clean the line code and process only 'fs' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('fs') and clean_code[-1].isdigit():
            fs_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_fs.append(line_code)
                
    # Render the form with fs_data
    return render_template('index.html', sixth_page=True, previous_page='page_five', next_page='page_seven', 
                           title="Floor Structure", 
                           fs_data=fs_data, preselected_fs=preselected_fs)

# Seventh page route - Plastering (ps)
@app.route('/page-seven', methods=['POST', 'GET'])
def page_seven():
    
    # Store the current page in the session
    session['last_visited'] = 'page_seven'
    
    if request.method == 'POST':
        #Store selected checkboxes into session
        selected_ps = request.form.getlist('ps')  # Get selected checkboxes for plastering
                                    
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
                                    
        # Clean the line code and process only 'ps' prefixed items
        clean_code = clean_line_code(line_code)
                                    
        if clean_code.startswith('ps') and clean_code[-1].isdigit():
            ps_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_ps.append(line_code)
                                            
    # Render the form with ps_data
    return render_template('index.html', seventh_page=True, previous_page='page_six', next_page='page_eight', 
                                                        title="Plastering", 
                                                        ps_data=ps_data, preselected_ps=preselected_ps)
                                                        
# Eighth page route - Internal Doors (id)
@app.route('/page-eight', methods=['POST', 'GET'])
def page_eight():
    
    # Store the current page in the session
    session['last_visited'] = 'page_eight'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_id = request.form.getlist('id')  # Get selected checkboxes for internal doors
        
        # Store the selected values into the session
        session['selected_id'] = selected_id
        
        # Get manual inputs for specific internal doors (e.g., id1 and id2)
        id1_manual_input = request.form.get('id1_manual_input')
        id2_manual_input = request.form.get('id2_manual_input')
        
        # Store manual inputs into session
        session['id1_manual_input'] = id1_manual_input
        session['id2_manual_input'] = id2_manual_input
        
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
        
        # Clean the line code and process only 'id' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('id') and clean_code[-1].isdigit():
            id_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_id.append(line_code)
                
    # Render the form with id_data
    return render_template('index.html', eighth_page=True, previous_page='page_seven', next_page='page_nine', 
                           title="Internal Doors", 
                           id_data=id_data, preselected_id=preselected_id)

# Ninth page route - Drainage (dr)
@app.route('/page-nine', methods=['POST', 'GET'])
def page_nine():
    
    # Store the current page in the session
    session['last_visited'] = 'page_nine'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_dr = request.form.getlist('dr')  # Get selected checkboxes for drainage
        
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
        
        # Clean the line code and process only 'dr' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('dr') and clean_code[-1].isdigit():
            dr_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_dr.append(line_code)
                
    # Render the form with dr_data
    return render_template('index.html', ninth_page=True, previous_page='page_eight', next_page='page_ten', 
                           title="Drainage", 
                           dr_data=dr_data, preselected_dr=preselected_dr)

# Tenth page route - Waste and Parking (wp)
@app.route('/page-ten', methods=['POST', 'GET'])
def page_ten():
    
    # Store the current page in the session
    session['last_visited'] = 'page_ten'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_wp = request.form.getlist('wp')  # Get selected checkboxes for waste and parking
        
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
        
        # Clean the line code and process only 'wp' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('wp') and clean_code[-1].isdigit():
            wp_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_wp.append(line_code)
                
    # Render the form with wp_data
    return render_template('index.html', tenth_page=True, previous_page='page_nine', next_page='page_eleven', 
                           title="Waste and Parking", 
                           wp_data=wp_data, preselected_wp=preselected_wp)

# Eleventh page route - Demolition Works (dw)
@app.route('/page-eleven', methods=['POST', 'GET'])
def page_eleven():
    
    # Store the current page in the session
    session['last_visited'] = 'page_eleven'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_dw = request.form.getlist('dw')  # Get selected checkboxes for demolition works
        
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
        
        # Clean the line code and process only 'dw' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('dw') and clean_code[-1].isdigit():
            dw_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_dw.append(line_code)
                
    # Render the form with dw_data
    return render_template('index.html', eleventh_page=True, previous_page='page_ten', next_page='page_twelve', 
                           title="Demolition Works", 
                           dw_data=dw_data, preselected_dw=preselected_dw)

# Twelfth page route - Further Requirements & Considerations (frc)
@app.route('/page-twelve', methods=['POST', 'GET'])
def page_twelve():
    
    # Store the current page in the session
    session['last_visited'] = 'page_twelve'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_frc = request.form.getlist('frc')  # Get selected checkboxes for further requirements & considerations
        
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
        
        # Clean the line code and process only 'frc' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('frc') and clean_code[-1].isdigit():
            frc_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_frc.append(line_code)
                
    # Render the form with frc_data
    return render_template('index.html', twelfth_page=True, previous_page='page_eleven', next_page='page_thirteen', 
                           title="Further Requirements & Considerations", 
                           frc_data=frc_data, preselected_frc=preselected_frc)

# Thirteenth page route - Additional Building Items (ab)
@app.route('/page-thirteen', methods=['POST', 'GET'])
def page_thirteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_thirteen'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_ab = request.form.getlist('ab')  # Get selected checkboxes for additional building items
        
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
        
        # Clean the line code and process only 'ab' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('ab') and clean_code[-1].isdigit():
            ab_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_ab.append(line_code)
                
    # Render the form with ab_data
    return render_template('index.html', thirteenth_page=True, previous_page='page_twelve', next_page='page_fourteen', 
                           title="Additional Building Items", 
                           ab_data=ab_data, preselected_ab=preselected_ab)

# Fourteenth page route - Schedule of Works (Weeks 1-8) (sww)
@app.route('/page-fourteen', methods=['POST', 'GET'])
def page_fourteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_fourteen'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_sww = request.form.getlist('sww')  # Get selected checkboxes for Schedule of Works (Weeks 1-8)
        
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
        
        # Clean the line code and process only 'sww' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('sww') and clean_code[-1].isdigit():
            sww_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_sww.append(line_code)
                
    # Render the form with sww_data
    return render_template('index.html', fourteenth_page=True, previous_page='page_thirteen', next_page='page_fifteen', 
                           title="Schedule of Works (Weeks 1-8)", 
                           sww_data=sww_data, preselected_sww=preselected_sww)

# Fifteenth page route - Schedule of Works (Week 9-12) (tww)
@app.route('/page-fifteen', methods=['POST', 'GET'])
def page_fifteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_fifteen'
    
    if request.method == 'POST':
        # Store selected checkboxes into session
        selected_tww = request.form.getlist('tww')  # Get selected checkboxes for Schedule of Works (Weeks 9-12)
        
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
        
        # Clean the line code and process only 'tww' prefixed items, excluding specified placeholders
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('tww') and clean_code[-1].isdigit() and line_code:
            tww_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_tww.append(line_code)
                
    # Render the form with tww_data
    return render_template('index.html', fifteenth_page=True, previous_page='page_fourteen', next_page='page_sixteen', 
                           title="Schedule of Works (Week 9-12)", 
                           tww_data=tww_data, preselected_tww=preselected_tww)

# Sixteenth page route - Pricing Categories (pc)
@app.route('/page-sixteen', methods=['POST', 'GET'])
def page_sixteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_sixteen'
    
    if request.method == 'POST':
        # Store selected pricing categories into session
        selected_pc = request.form.getlist('pc')  # Get selected checkboxes for pricing categories
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
        
        # Clean the line code and process only 'pc' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('pc') and clean_code[-1].isdigit():
            pc_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_pc.append(line_code)
                
    # Render the form with pc_data
    return render_template('index.html', sixteenth_page=True, previous_page='page_fifteen', next_page='page_seventeen', 
                           title="Pricing Categories", 
                           pc_data=pc_data, preselected_pc=preselected_pc)

# Seventeenth page route - Electrics (el) - Only shown if pc4 is selected
@app.route('/page-seventeen', methods=['POST', 'GET'])
def page_seventeen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_seventeen'
    
    if request.method == 'POST':
        # Collect manual input values for electrics
        session['el1_manual_input'] = request.form.get('el1_manual_input')
        session['el2_manual_input'] = request.form.get('el2_manual_input')
        session['el3_manual_input'] = request.form.get('el3_manual_input')
        session['el4_manual_input'] = request.form.get('el4_manual_input')
        
        # Store selected electrics checkboxes into session
        selected_el = request.form.getlist('el')  # Get selected checkboxes for electrics
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
        
        # Clean the line code and process only 'el' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('el') and clean_code[-1].isdigit():
            el_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_el.append(line_code)
                
    # Render the form with el_data
    return render_template('index.html', seventeenth_page=True, previous_page='page_sixteen', next_page='page_eighteen', 
                           title="Electrics", 
                           el_data=el_data, preselected_el=preselected_el)
                            
# Eighteenth page route - Plumbing (pl)
@app.route('/page-eighteen', methods=['POST', 'GET'])
def page_eighteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_eighteen'
    
    if request.method == 'POST':
        # Store selected plumbing options into session
        selected_pl = request.form.getlist('pl')  # Get selected checkboxes for plumbing
        
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
        
        # Clean the line code and process only 'pl' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('pl') and clean_code[-1].isdigit():
            pl_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_pl.append(line_code)
                
    # Render the form with pl_data
    return render_template('index.html', eighteenth_page=True, previous_page='page_seventeen', next_page='page_nineteen', 
                           title="Plumbing", 
                           pl_data=pl_data, preselected_pl=preselected_pl)
                            

# Nineteenth page route - Skylights (sl)
@app.route('/page-nineteen', methods=['POST', 'GET'])
def page_nineteen():
    
    # Store the current page in the session
    session['last_visited'] = 'page_nineteen'
    
    if request.method == 'POST':
        # Store selected skylights options into session
        selected_sl = request.form.getlist('sl')  # Get selected checkboxes for skylights
        session['selected_sl'] = selected_sl  # Store the selected values into the session
        
        return redirect(url_for('page_twenty'))  # Go to the next page (page twenty)
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    sl_data = {}
    preselected_sl = []
    
    # Filter the relevant rows based on 'sl' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'sl' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('sl') and clean_code[-1].isdigit():
            sl_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_sl.append(line_code)
        
    # Render the form with sl_data
    return render_template('index.html', nineteenth_page=True, previous_page='page_eighteen', next_page='page_twenty',      title="Skylights", 
            sl_data=sl_data, preselected_sl=preselected_sl)

# Twentieth page route - Velux Windows (vl) - Only shown if pc7 is selected
@app.route('/page-twenty', methods=['POST', 'GET'])
def page_twenty():
    
    # Store the current page in the session
    session['last_visited'] = 'page_twenty'
    
    if request.method == 'POST':
        # Store selected velux windows options into session
        selected_vl = request.form.getlist('vl')  # Get selected checkboxes for velux windows
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
        
        # Clean the line code and process only 'vl' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('vl') and clean_code[-1].isdigit():
            vl_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_vl.append(line_code)
                
    # Render the form with vl_data
    return render_template('index.html', twentieth_page=True, previous_page='page_nineteen', next_page='page_twenty_one', 
                           title="Velux Windows", 
                           vl_data=vl_data, preselected_vl=preselected_vl)

# Twenty-first page route - Aluminium Capping (ac) - Only shown if pc8 is selected
@app.route('/page-twenty_one', methods=['POST', 'GET'])
def page_twenty_one():
    
    if request.method == 'POST':
        # Store selected aluminium capping options into session
        selected_ac = request.form.getlist('ac')  # Get selected checkboxes for aluminium capping
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
        
        # Clean the line code and process only 'ac' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('ac') and clean_code[-1].isdigit():
            ac_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_ac.append(line_code)
                
    # Render the form with ac_data
    return render_template('index.html', twenty_first_page=True, previous_page='page_twenty', next_page='page_twenty_two', 
                           title="Aluminium Capping", 
                           ac_data=ac_data, preselected_ac=preselected_ac)

# Twenty-second page route - Glass Valley (gv) - Only shown if pc9 is selected
@app.route('/page-twenty_two', methods=['POST', 'GET'])
def page_twenty_two():
    
    if request.method == 'POST':
        # Store selected glass valley options into session
        selected_gv = request.form.getlist('gv')  # Get selected checkboxes for glass valley
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
        
        # Clean the line code and process only 'gv' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('gv') and clean_code[-1].isdigit():
            gv_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_gv.append(line_code)
                
    # Render the form with gv_data
    return render_template('index.html', twenty_second_page=True, previous_page='page_twenty_one', next_page='page_twenty_three', 
                           title="Glass Valley", 
                           gv_data=gv_data, preselected_gv=preselected_gv)

# Twenty-third page route - SLiding Doors (sds, sd)
@app.route('/page_twenty_three', methods=['POST', 'GET'])
def page_twenty_three():
    if request.method == 'POST':
        
        # Store the manual input for dm5
        dm5_manual_input = request.form.get('dm5_manual_input')
        session['dm5_manual_input'] = dm5_manual_input
        
        # Store selected checkboxes for sds
        selected_sds = request.form.getlist('sds')
        session['selected_sds'] = selected_sds
        
        # Store selected option from the dropdown for sd
        selected_sd = request.form.get('selected_sd')
        session['selected_sd'] = selected_sd
        
        # Write manual input for dm5 to the dimension column (index 10)
        sheet_data = fetch_data()
        for row_index, row in enumerate(sheet_data, start=2):  # Start from row 2 to skip header
            if row.get('Line Code') == 'dm5':
                sheet.update_cell(row_index, 10, dm5_manual_input)  # Column 10 for dimensions
                
        return redirect(url_for('page_twenty_four'))  # Move to the next page
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    sds_data = {}
    preselected_sds = []
    sd_options = []
    
    # Find the description for dm5 and prepare the label
    dm5_label = ''
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        
        # Find the label for dm5 (from the description column)
        if line_code == 'dm5':
            dm5_label = internal_description
            
        # Handle sds prefix for checkboxes
        clean_code = clean_line_code(line_code)
        if clean_code.startswith('sds') and clean_code[-1].isdigit():
            sds_data[line_code] = {'description': internal_description}
            if row.get('Include') == 'Y':
                preselected_sds.append(line_code)
                
        # Handle sd prefix for the dropdown options
        if clean_code.startswith('sd') and clean_code[-1].isdigit():
            sd_options.append({'line_code': line_code, 'description': internal_description})
            
    # Render the form with the necessary data
    return render_template('index.html', twenty_third_page=True, previous_page='page_twenty_two', next_page='page_twenty_four',
                           title="Sliding Doors",
                           dm5_label=dm5_label, sds_data=sds_data, preselected_sds=preselected_sds, sd_options=sd_options)

# Twenty-fourth page route - Optional Extras (oe)
@app.route('/page_twenty_four', methods=['POST', 'GET'])
def page_twenty_four():
    session['last_visited'] = 'page_twenty_four'
    
    if request.method == 'POST':
        # Store selected checkboxes for Optional Extras into session
        selected_oe = request.form.getlist('oe')  # Get selected checkboxes for Optional Extras
        session['selected_oe'] = selected_oe  # Store the selected values into the session
        
        return redirect(url_for('page_twenty_five'))  # Redirect to the next page
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    oe_data = {}
    preselected_oe = []
    
    # Filter the relevant rows based on 'oe' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'oe' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('oe') and clean_code[-1].isdigit():
            oe_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_oe.append(line_code)
                
    # Render the form with oe_data
    return render_template('index.html', twenty_fourth_page=True, previous_page='page_twenty_three', next_page='page_twenty_five', 
                           title="Optional Extras", 
                           oe_data=oe_data, preselected_oe=preselected_oe)

# Twenty-fifth page route - Contingency (co)
@app.route('/page_twenty_five', methods=['POST', 'GET'])
def page_twenty_five():
    session['last_visited'] = 'page_twenty_five'
    
    if request.method == 'POST':
        # Store selected checkboxes for Contingency into session
        selected_co = request.form.getlist('co')  # Get selected checkboxes for Contingency
        session['selected_co'] = selected_co  # Store the selected values into the session
        
        return redirect(url_for('page_twenty_six'))  # Redirect to the next page (Finishing Works)
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    co_data = {}
    preselected_co = []
    
    # Filter the relevant rows based on 'co' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'co' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('co') and clean_code[-1].isdigit():
            co_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_co.append(line_code)
                
    # Render the form with co_data
    return render_template('index.html', twenty_fifth_page=True, previous_page='page_twenty_four', next_page='page_twenty_six', 
                           title="Contingency", 
                           co_data=co_data, preselected_co=preselected_co)
                            

# Twenty-sixth page route - Finishing Works (fw)
@app.route('/page_twenty_six', methods=['POST', 'GET'])
def page_twenty_six():
    session['last_visited'] = 'page_twenty_six'
    
    if request.method == 'POST':
        # Store selected checkboxes for Finishing Works into session
        selected_fw = request.form.getlist('fw')  # Get selected checkboxes for Finishing Works
        session['selected_fw'] = selected_fw  # Store the selected values into the session
        
        return redirect(url_for('page_twenty_seven'))  # Redirect to the next page (Finishing Works Optional Extras)
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    fw_data = {}
    preselected_fw = []
    
    # Filter the relevant rows based on 'fw' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'fw' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('fw') and clean_code[-1].isdigit():
            fw_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_fw.append(line_code)
                
    # Render the form with fw_data
    return render_template('index.html', twenty_sixth_page=True, previous_page='page_twenty_five', next_page='page_twenty_seven', 
                           title="Finishing Works", 
                           fw_data=fw_data, preselected_fw=preselected_fw)

# Twenty-seventh page route - Finishing Works Optional Extras (foe)
@app.route('/page_twenty_seven', methods=['POST', 'GET'])
def page_twenty_seven():
    session['last_visited'] = 'page_twenty_seven'
    
    if request.method == 'POST':
        # Store selected checkboxes for Finishing Works Optional Extras into session
        selected_foe = request.form.getlist('foe')  # Get selected checkboxes for Finishing Works Optional Extras
        session['selected_foe'] = selected_foe  # Store the selected values into the session
        
        return redirect(url_for('page_twenty_eight'))  # Redirect to the next page (Notes)
    
    # Load data from Google Sheets
    sheet_data = fetch_data()
    foe_data = {}
    preselected_foe = []
    
    # Filter the relevant rows based on 'foe' prefix
    for row in sheet_data:
        line_code = row.get('Line Code', '')
        internal_description = row.get('Internal Description', '')
        include = row.get('Include', '')
        
        # Clean the line code and process only 'foe' prefixed items
        clean_code = clean_line_code(line_code)
        
        if clean_code.startswith('foe') and clean_code[-1].isdigit():
            foe_data[line_code] = {'description': internal_description, 'is_included': include == 'Y'}
            if include == 'Y':
                preselected_foe.append(line_code)
                
    # Render the form with foe_data
    return render_template('index.html', twenty_seventh_page=True, previous_page='page_twenty_six', next_page='page_twenty_eight', 
                           title="Finishing Works Optional Extras", 
                           foe_data=foe_data, preselected_foe=preselected_foe)

# Twenty-eighth page route - Additional Notes (an)
@app.route('/page_twenty_eight', methods=['POST', 'GET'])
def page_twenty_eight():
    session['last_visited'] = 'page_twenty_eight'
    
    if request.method == 'POST':
        # Store manual inputs for Additional Notes into session
        session['an1_manual_input'] = request.form.get('an1_manual_input')
        session['an2_manual_input'] = request.form.get('an2_manual_input')
        session['an3_manual_input'] = request.form.get('an3_manual_input')
        session['an4_manual_input'] = request.form.get('an4_manual_input')
        session['an5_manual_input'] = request.form.get('an5_manual_input')
        session['an6_manual_input'] = request.form.get('an6_manual_input')
        session['an7_manual_input'] = request.form.get('an7_manual_input')
        
        return redirect(url_for('review'))  # Redirect to the review page
    
    # Render the form
    return render_template('index.html', twenty_eighth_page=True, previous_page='page_twenty_seven', next_page='review', 
                           title="Additional Notes",
                           an1_manual_input=session.get('an1_manual_input', ''),
                           an2_manual_input=session.get('an2_manual_input', ''),
                           an3_manual_input=session.get('an3_manual_input', ''),
                           an4_manual_input=session.get('an4_manual_input', ''),
                           an5_manual_input=session.get('an5_manual_input', ''),
                           an6_manual_input=session.get('an6_manual_input', ''),
                           an7_manual_input=session.get('an7_manual_input', ''))
                            
@app.route('/review', methods=['GET', 'POST'])
def review():
    if request.method == 'POST':
        return redirect(url_for('submit'))
    
    # Fetch all session data to display on the review page
    review_data = {
        'selected_special_notes': session.get('selected_special_notes'),
        'selected_building_works': session.get('selected_building_works'),
        'selected_boundary_lines': session.get('selected_boundary_lines'),
        'selected_co': session.get('selected_co'),
        'selected_fw': session.get('selected_fw'),
        'selected_fwoe': session.get('selected_fwoe'),
        'selected_ew': session.get('selected_ew'),
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
        'selected_sl': session.get('selected_sl'),
        'selected_vl': session.get('selected_vl'),
        'selected_ac': session.get('selected_ac'),
        'selected_gv': session.get('selected_gv'),
        'selected_sds': session.get('selected_sds'),
        'selected_sd': session.get('selected_sd'),
        
        # Manual inputs
        'address': session.get('address'),
        'date': session.get('date'),
        'nb1_manual_input': session.get('nb1_manual_input'),
        'nb2_manual_input': session.get('nb2_manual_input'),
        'dm1_manual_input': session.get('dm1_manual_input'),
        'dm2_manual_input': session.get('dm2_manual_input'),
        'dm3_manual_input': session.get('dm3_manual_input'),
        'dm4_manual_input': session.get('dm4_manual_input'),
        'dm5_manual_input': session.get('dm5_manual_input'),
        'cs1_manual_input': session.get('cs1_manual_input'),
        'an1_manual_input': session.get('an1_manual_input'),
        'an2_manual_input': session.get('an2_manual_input'),
        'an3_manual_input': session.get('an3_manual_input'),
        'an4_manual_input': session.get('an4_manual_input'),
        'an5_manual_input': session.get('an5_manual_input'),
        'an6_manual_input': session.get('an6_manual_input'),
        'an7_manual_input': session.get('an7_manual_input')
    }
    
    # Fetch internal descriptions for selected items
    internal_descriptions = fetch_internal_descriptions(review_data)  # Ensure transformation here
    
    # Create a dictionary with readable titles
    review_with_titles = {TITLE_MAPPING.get(key, key): value for key, value in internal_descriptions.items()}
    
    # Pass TITLE_MAPPING and other data to the template
    return render_template('index.html', review_page=True, review_data=review_with_titles, TITLE_MAPPING=TITLE_MAPPING, title="Review Page")

# Assuming confirm_data is needed as part of validation
@app.route('/confirm_data', methods=['POST'])
def confirm_data():
    # You can handle the data confirmation logic here
    # For now, let's assume you simply return a success message
    try:
        # Logic to confirm data before final submission
        # You can add logic here to validate or process session data if needed
        return "Data confirmed successfully", 200
    except Exception as e:
        return f"Error: {e}", 500
    
    
@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        print(request.form) 
        try:
            # Ensure all session keys are initialized if they are not set
            session.setdefault('selected_special_notes', [])
            session.setdefault('selected_building_works', [])
            session.setdefault('selected_boundary_lines', [])
            session.setdefault('selected_co', [])
            session.setdefault('selected_fw', [])
            session.setdefault('selected_foe', [])
            session.setdefault('selected_ew', [])
            session.setdefault('selected_fs', [])
            session.setdefault('selected_ps', [])
            session.setdefault('selected_id', [])
            session.setdefault('selected_dr', [])
            session.setdefault('selected_wp', [])
            session.setdefault('selected_dw', [])
            session.setdefault('selected_frc', [])
            session.setdefault('selected_ab', [])
            session.setdefault('selected_sww', [])
            session.setdefault('selected_tww', [])
            session.setdefault('selected_pc', [])
            session.setdefault('selected_el', [])
            session.setdefault('selected_pl', [])
            session.setdefault('selected_sl', [])
            session.setdefault('selected_vl', [])
            session.setdefault('selected_ac', [])
            session.setdefault('selected_gv', [])
            session.setdefault('selected_sds', [])
            session.setdefault('selected_sd', [])
            
            # Retrieve all session data for the final update
            selected_special_notes = session.get('selected_special_notes', [])
            selected_building_works = session.get('selected_building_works', [])
            selected_boundary_lines = session.get('selected_boundary_lines', [])
            selected_co = session.get('selected_co', [])
            selected_fw = session.get('selected_fw', [])
            selected_foe = session.get('selected_foe', [])
            selected_ew = session.get('selected_ew', [])
            selected_fs = session.get('selected_fs', [])
            selected_ps = session.get('selected_ps', [])
            selected_id = session.get('selected_id', [])
            selected_dr = session.get('selected_dr', [])
            selected_wp = session.get('selected_wp', [])
            selected_dw = session.get('selected_dw', [])
            selected_frc = session.get('selected_frc', [])
            selected_ab = session.get('selected_ab', [])
            selected_sww = session.get('selected_sww', [])
            selected_tww = session.get('selected_tww', [])
            selected_pc = session.get('selected_pc', [])
            selected_el = session.get('selected_el', [])
            selected_pl = session.get('selected_pl', [])
            selected_sl = session.get('selected_sl', [])
            selected_vl = session.get('selected_vl', [])
            selected_ac = session.get('selected_ac', [])
            selected_gv = session.get('selected_gv', [])
            selected_sds = session.get('selected_sds', [])
            selected_sd = session.get('selected_sd', [])
            
            address = session.get('address')
            date = session.get('date')
            
            # Manual inputs
            nb1_manual_input = session.get('nb1_manual_input')
            nb2_manual_input = session.get('nb2_manual_input')
            dm1_manual_input = session.get('dm1_manual_input')
            dm2_manual_input = session.get('dm2_manual_input')
            dm3_manual_input = session.get('dm3_manual_input')
            dm4_manual_input = session.get('dm4_manual_input')
            cs1_manual_input = session.get('cs1_manual_input')
            dm5_manual_input = session.get('dm5_manual_input')
            an1_manual_input = session.get('an1_manual_input')
            an2_manual_input = session.get('an2_manual_input')
            an3_manual_input = session.get('an3_manual_input')
            an4_manual_input = session.get('an4_manual_input')
            an5_manual_input = session.get('an5_manual_input')
            an6_manual_input = session.get('an6_manual_input')
            an7_manual_input = session.get('an7_manual_input')
            
            # Combine data from all pages
            combined_data = (
                selected_special_notes +
                selected_building_works +
                selected_boundary_lines +
                selected_co +
                selected_fw +
                selected_foe +
                selected_ew +
                selected_fs +
                selected_ps +
                selected_id +
                selected_dr +
                selected_wp +
                selected_dw +
                selected_frc +
                selected_ab +
                selected_sww +
                selected_tww +
                selected_pc +
                selected_el +
                selected_pl +
                selected_sl +
                selected_vl +
                selected_ac +
                selected_gv +
                selected_sds +
                [selected_sd]  # Dropdown option, so it's a single value
            )     
            
            # Call confirm_data before proceeding to update
            confirm_response = confirm_data()
            if confirm_response[1] == 200:
            
                # Perform the batch update to the Google Sheet
                update_include_column(combined_data)  # Only update once, at the end
            
                # Update the placeholders in the Google Sheet for address, date, and manual inputs
                update_description_column(
                    address, date, nb1_manual_input, nb2_manual_input, 
                    dm1_manual_input, dm2_manual_input, dm3_manual_input, 
                    dm4_manual_input, dm5_manual_input, cs1_manual_input,
                    an1_manual_input, an2_manual_input, an3_manual_input,
                    an4_manual_input, an5_manual_input, an6_manual_input,
                    an7_manual_input
            )
            
                # Return confirmation message for successful data upload
                # Then redirect to the production script trigger
                flash("Data uploaded successfully. You may now publish your quote.")  # Flash success message for user
                return redirect(url_for('trigger_production'))  # Redirect to trigger the production script
            
            else:
                flash("Data confirmation failed. Please try again.")
                return redirect(url_for('review'))
        
        except Exception as e:
            print(f"Error during confirmation: {str(e)}")  # Log the error message once
            return "Something went wrong, please try again.", 500
    

#final production trigger
@app.route('/trigger_production')
def trigger_production():
    try:
        # Call the QM_Production.py script using subprocess
        result = subprocess.run(['python3', 'QM_Production.py'], capture_output=True, text=True)
        
        # Check if the script ran successfully
        if result.returncode == 0:
            
            # Capture the URL from the production script's stdout (extracting the part after "Document link: ")
            output = result.stdout.strip()
            if "Document link:" in output:
                document_url = output.split("Document link: ")[-1].strip()
            else:
                document_url = "No valid document link found."
                    
            # If a valid URL is found, display it as a button; otherwise, show an error
            if document_url:
                return f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Great Job!</title>
                    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">  <!-- Link your CSS file -->
                    </head>
                    <body>
                        <h2>Your document is ready!</h2>
                        <p>
                            <a href="{document_url}" target="_blank" class="btn">Click here to open it in a new tab</a>
                        </p>
                        </body>
                        </html>
                        """
                
            else:
                    return "No valid document link found.", 500
                
        else:
            return f"Error in production script: {result.stderr}", 500
                
    except Exception as e:
        return f"Error: {e}", 500    

if __name__ == '__main__':
    app.run(debug=True)
    
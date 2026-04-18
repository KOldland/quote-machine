#!/usr/bin/env python3

# Built-in Modules
import os
import re
import subprocess
import time
import json
from datetime import datetime
from PIL import Image
import traceback

# Third-party Modules
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import gspread
from google.oauth2.service_account import Credentials
from templates import get_layout_definition
from pathlib import Path
from copy import deepcopy
from template_store import (
	initialize_template_store,
	load_template_payload,
	get_latest_template_version,
	get_template_store_status,
	get_template_store_overview,
	clone_template,
)

app = Flask(__name__)
csrf = CSRFProtect(app)


def is_truthy_env(name: str) -> bool:
	return os.getenv(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


TEST_MODE = is_truthy_env('QM_TEST_MODE')

# Define upload folder path
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB total (if batch)
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
app.config['SESSION_FILE_DIR'] = str(Path(__file__).parent / 'flask_session')
app.config['SECRET_KEY'] = os.getenv('QM_SECRET_KEY', 'dev-insecure-key-change-me')

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
	os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize the session extension
Session(app)

# Set up Google Sheets API credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def build_mock_sheet_data():
	# Minimal dataset that keeps route rendering and submit flow functional in test mode.
	line_codes = [
		('sn1', 'Special note test'),
		('bw1', 'Building works test'),
		('pp1', 'Planning status test'),
		('cs1', 'Council test'),
		('ew1', 'External wall test'),
		('er1', 'Roofing test'),
		('id1', 'Internal door test'),
		('dr1', 'Drainage test'),
		('wp1', 'Waste and parking test'),
		('frc1', 'Further requirements test'),
		('dw1', 'Demolition works test'),
		('fs1', 'Floor structure test'),
		('gv1', 'Glass valley test'),
		('rro1', 'Rear reception opening test'),
		('iw1', 'Internal wall test'),
		('ab1', 'Additional building work test'),
		('el1', 'Electrics test'),
		('pl1', 'Plumbing test'),
		('sk1', 'Skylight test'),
		('vl1', 'Velux test'),
		('ac1', 'Aluminium capping test'),
		('sld1', 'Sliding doors test'),
		('oe1', 'Optional extras test'),
		('fw1', 'Finishing works test'),
	]
	return [
		{
			'Line Code': code,
			'Internal Description': description,
			'Include': 'N',
			'description': '',
		}
		for code, description in line_codes
	]


if TEST_MODE:
	client = None
	spreadsheet_id = os.getenv('QM_SPREADSHEET_ID', 'TEST_SPREADSHEET')
	sheet = None
	mock_sheet_data = build_mock_sheet_data()
else:
	# Load credentials path from environment first, with local app fallback
	creds_path = os.getenv('QM_CREDENTIALS_PATH', str(Path(__file__).with_name('QM_credentials.json')))
	if not os.path.exists(creds_path):
		raise FileNotFoundError(
			"Google credentials file not found. Set QM_CREDENTIALS_PATH or place QM_credentials.json in the app directory."
		)

	# Initialize Google Sheets client
	creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
	client = gspread.authorize(creds)
	spreadsheet_id = os.getenv('QM_SPREADSHEET_ID', '1gscALSOGoaEYyuUN0zyu_pRAMvjjJvWjv3ZnAFCd5rQ')
	sheet = client.open_by_key(spreadsheet_id).sheet1

# Load layout intent metadata
intent_path = Path(__file__).parent / 'layout_intents.json'
with intent_path.open() as f:
	layout_intents = json.load(f)

# Load page schema metadata for builder-driven rendering.
page_schema_path = Path(__file__).parent / 'page_schemas.json'
with page_schema_path.open() as f:
	page_schemas = json.load(f)

TEMPLATE_STORE_KEY = os.getenv('QM_TEMPLATE_KEY', 'first_client_template_v1')
TEMPLATE_STORE_READ_ENABLED = is_truthy_env('QM_TEMPLATE_STORE_READ')

try:
	template_store_bootstrap = initialize_template_store(page_schemas, template_key=TEMPLATE_STORE_KEY)
	print(
		"Template store ready:",
		f"pages={template_store_bootstrap.get('pages', 0)}",
		f"questions={template_store_bootstrap.get('questions', 0)}",
		f"db={template_store_bootstrap.get('db_path', '')}",
	)
except Exception as exc:
	template_store_bootstrap = {'error': str(exc)}
	print(f"Template store bootstrap skipped: {exc}")

if TEMPLATE_STORE_READ_ENABLED:
	try:
		db_payload = load_template_payload(template_key=TEMPLATE_STORE_KEY)
		if db_payload:
			page_schemas = db_payload
			print(
				"Template store read enabled:",
				f"template={TEMPLATE_STORE_KEY}",
				f"version={get_latest_template_version(TEMPLATE_STORE_KEY)}",
			)
		else:
			print("Template store read enabled, but no payload found. Using JSON schema file.")
	except Exception as exc:
		print(f"Template store read failed, falling back to JSON schema: {exc}")


SUPPORTED_SCHEMA_FIELD_TYPES = {'checkbox_group'}

DEFAULT_PRICING_RULES = {
	'kitchen_light_rate': 30.0,
	'kitchen_point_rate': 65.0,
	'loft_light_rate': 30.0,
	'loft_point_rate': 65.0,
	'rounding_precision': 2,
}

DEFAULT_PAYMENT_PLAN_RULES = {
	'deposit_percent': 10.0,
	'stages': [
		{'name': 'Weeks 1-8', 'percent': 50.0},
		{'name': 'Weeks 9-12', 'percent': 30.0},
		{'name': 'Completion', 'percent': 10.0},
	],
}


def get_builder_settings():
	settings = page_schemas.setdefault('settings', {})
	if not isinstance(settings, dict):
		settings = {}
		page_schemas['settings'] = settings
	return settings


def ensure_builder_settings_defaults():
	settings = get_builder_settings()

	pricing_rules = settings.get('pricing_rules')
	if not isinstance(pricing_rules, dict):
		settings['pricing_rules'] = deepcopy(DEFAULT_PRICING_RULES)
	else:
		for key, default_value in DEFAULT_PRICING_RULES.items():
			pricing_rules.setdefault(key, default_value)

	payment_plan_rules = settings.get('payment_plan_rules')
	if not isinstance(payment_plan_rules, dict):
		settings['payment_plan_rules'] = deepcopy(DEFAULT_PAYMENT_PLAN_RULES)
	else:
		payment_plan_rules.setdefault('deposit_percent', DEFAULT_PAYMENT_PLAN_RULES['deposit_percent'])
		stages = payment_plan_rules.get('stages')
		if not isinstance(stages, list) or len(stages) != 3:
			payment_plan_rules['stages'] = deepcopy(DEFAULT_PAYMENT_PLAN_RULES['stages'])


def _parse_builder_float(value, default_value, min_value=None, max_value=None):
	number = to_float(value, default_value)
	if min_value is not None:
		number = max(number, min_value)
	if max_value is not None:
		number = min(number, max_value)
	return number


def _parse_builder_int(value, default_value, min_value=None, max_value=None):
	try:
		number = int(str(value).strip())
	except (ValueError, TypeError):
		number = int(default_value)
	if min_value is not None:
		number = max(number, min_value)
	if max_value is not None:
		number = min(number, max_value)
	return number


def get_pricing_rules():
	ensure_builder_settings_defaults()
	stored_rules = get_builder_settings().get('pricing_rules', {})
	rules = deepcopy(DEFAULT_PRICING_RULES)
	rules['kitchen_light_rate'] = _parse_builder_float(stored_rules.get('kitchen_light_rate'), rules['kitchen_light_rate'], 0, 10000)
	rules['kitchen_point_rate'] = _parse_builder_float(stored_rules.get('kitchen_point_rate'), rules['kitchen_point_rate'], 0, 10000)
	rules['loft_light_rate'] = _parse_builder_float(stored_rules.get('loft_light_rate'), rules['loft_light_rate'], 0, 10000)
	rules['loft_point_rate'] = _parse_builder_float(stored_rules.get('loft_point_rate'), rules['loft_point_rate'], 0, 10000)
	rules['rounding_precision'] = _parse_builder_int(stored_rules.get('rounding_precision'), rules['rounding_precision'], 0, 4)
	return rules


def get_payment_plan_rules():
	ensure_builder_settings_defaults()
	stored_rules = get_builder_settings().get('payment_plan_rules', {})
	rules = deepcopy(DEFAULT_PAYMENT_PLAN_RULES)
	rules['deposit_percent'] = _parse_builder_float(stored_rules.get('deposit_percent'), rules['deposit_percent'], 0, 100)

	stored_stages = stored_rules.get('stages', [])
	parsed_stages = []
	for index, default_stage in enumerate(DEFAULT_PAYMENT_PLAN_RULES['stages']):
		stored_stage = stored_stages[index] if index < len(stored_stages) and isinstance(stored_stages[index], dict) else {}
		stage_name = str(stored_stage.get('name', default_stage['name'])).strip() or default_stage['name']
		stage_percent = _parse_builder_float(stored_stage.get('percent'), default_stage['percent'], 0, 100)
		parsed_stages.append({'name': stage_name, 'percent': stage_percent})

	rules['stages'] = parsed_stages
	return rules


def calculate_payment_plan(total_amount, payment_plan_rules):
	total = max(to_float(total_amount, 0.0), 0.0)
	precision = _parse_builder_int(get_pricing_rules().get('rounding_precision', 2), 2, 0, 4)
	entries = [
		{'name': 'Deposit', 'percent': _parse_builder_float(payment_plan_rules.get('deposit_percent'), 0.0, 0, 100)}
	]
	entries.extend(payment_plan_rules.get('stages', []))

	plan_entries = []
	running_amount = 0.0
	for index, entry in enumerate(entries):
		name = str(entry.get('name', f'Stage {index + 1}')).strip() or f'Stage {index + 1}'
		percent = _parse_builder_float(entry.get('percent'), 0.0, 0, 100)
		if index == len(entries) - 1:
			amount = round(total - running_amount, precision)
		else:
			amount = round(total * (percent / 100.0), precision)
			running_amount += amount

		plan_entries.append({
			'name': name,
			'percent': round(percent, 2),
			'amount': amount,
		})

	return {
		'total_amount': round(total, precision),
		'entries': plan_entries,
	}


def validate_page_schema(page_schema):
	if not page_schema:
		return False

	if not page_schema.get('id'):
		return False

	fields = page_schema.get('fields', [])
	if not isinstance(fields, list):
		return False

	seen_ids = set()
	for field in fields:
		field_id = field.get('id')
		field_type = field.get('type')
		field_name = field.get('name')
		if not field_id or not field_type or not field_name:
			return False
		if field_id in seen_ids:
			return False
		if field_type not in SUPPORTED_SCHEMA_FIELD_TYPES:
			return False
		seen_ids.add(field_id)

	return True


def get_page_schema(page_id):
	page_schema = deepcopy(page_schemas.get('pages', {}).get(page_id))
	if not validate_page_schema(page_schema):
		return None
	return page_schema


def save_page_schemas():
	with page_schema_path.open('w') as f:
		json.dump(page_schemas, f, indent=2)

	# Keep Template Store in sync with latest builder edits (Phase 1/2 bootstrap path).
	try:
		initialize_template_store(page_schemas, template_key=TEMPLATE_STORE_KEY)
	except Exception as exc:
		print(f"Template store sync skipped after save: {exc}")


def update_builder_draft_from_form(form_data):
	warnings = []
	pages = page_schemas.get('pages', {})
	for page_id, page in pages.items():
		# Page title
		new_title = form_data.get(f'page_title__{page_id}', '').strip()
		if new_title:
			page['title'] = new_title

		# Navigation endpoints — validate they look like a Flask route name (alphanumeric + underscores)
		new_prev = form_data.get(f'page_prev__{page_id}', '').strip()
		new_next = form_data.get(f'page_next__{page_id}', '').strip()
		import re as _re
		_valid_endpoint = _re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
		if new_prev:
			if _valid_endpoint.match(new_prev):
				page['navigation']['previous_endpoint'] = new_prev
			else:
				warnings.append(f"Invalid previous endpoint '{new_prev}' for {page_id} — must be a route name.")
		if new_next:
			if _valid_endpoint.match(new_next):
				page['navigation']['next_endpoint'] = new_next
			else:
				warnings.append(f"Invalid next endpoint '{new_next}' for {page_id} — must be a route name.")

		# Field labels and ordering
		updated_fields = []
		for index, field in enumerate(page.get('fields', [])):
			label_key = f"label__{page_id}__{index}"
			order_key = f"order__{page_id}__{index}"
			updated_field = deepcopy(field)

			new_label = form_data.get(label_key, '').strip()
			if new_label:
				updated_field['label'] = new_label

			try:
				order_value = int(form_data.get(order_key, str(index)))
			except ValueError:
				order_value = index

			updated_fields.append((order_value, updated_field))

		updated_fields.sort(key=lambda item: item[0])
		page['fields'] = [item[1] for item in updated_fields]

	settings = get_builder_settings()

	pricing_rules = settings.setdefault('pricing_rules', deepcopy(DEFAULT_PRICING_RULES))
	pricing_rules['kitchen_light_rate'] = _parse_builder_float(form_data.get('rules__kitchen_light_rate'), pricing_rules.get('kitchen_light_rate', 30.0), 0, 10000)
	pricing_rules['kitchen_point_rate'] = _parse_builder_float(form_data.get('rules__kitchen_point_rate'), pricing_rules.get('kitchen_point_rate', 65.0), 0, 10000)
	pricing_rules['loft_light_rate'] = _parse_builder_float(form_data.get('rules__loft_light_rate'), pricing_rules.get('loft_light_rate', 30.0), 0, 10000)
	pricing_rules['loft_point_rate'] = _parse_builder_float(form_data.get('rules__loft_point_rate'), pricing_rules.get('loft_point_rate', 65.0), 0, 10000)
	pricing_rules['rounding_precision'] = _parse_builder_int(form_data.get('rules__rounding_precision'), pricing_rules.get('rounding_precision', 2), 0, 4)

	payment_plan_rules = settings.setdefault('payment_plan_rules', deepcopy(DEFAULT_PAYMENT_PLAN_RULES))
	deposit_percent = _parse_builder_float(form_data.get('rules__deposit_percent'), payment_plan_rules.get('deposit_percent', 10.0), 0, 100)

	candidate_stages = []
	for stage_index, default_stage in enumerate(DEFAULT_PAYMENT_PLAN_RULES['stages'], start=1):
		name_key = f'rules__stage_{stage_index}_name'
		percent_key = f'rules__stage_{stage_index}_percent'
		stage_name = form_data.get(name_key, default_stage['name']).strip() or default_stage['name']
		stage_percent = _parse_builder_float(form_data.get(percent_key), default_stage['percent'], 0, 100)
		candidate_stages.append({'name': stage_name, 'percent': stage_percent})

	total_percent = deposit_percent + sum(stage['percent'] for stage in candidate_stages)
	if round(total_percent, 2) != 100.0:
		warnings.append('Payment plan not saved: deposit + stage percentages must equal 100%.')
	else:
		payment_plan_rules['deposit_percent'] = deposit_percent
		payment_plan_rules['stages'] = candidate_stages

	# Page reorder — submitted as comma-separated list of page_ids from drag-and-drop
	page_order_str = form_data.get('page_order', '').strip()
	if page_order_str:
		ordered_ids = [pid.strip() for pid in page_order_str.split(',') if pid.strip() in pages]
		if len(ordered_ids) == len(pages):
			page_schemas['pages'] = {pid: pages[pid] for pid in ordered_ids}

	save_page_schemas()
	return warnings


ensure_builder_settings_defaults()


def build_schema_checkbox_group(field_schema, sheet_data, checkbox_data):
	storage_key = field_schema.get('storage', {}).get('key', field_schema['name'])
	preselected = checkbox_data.get(storage_key, {}).get('preselected', []).copy()
	source = field_schema.get('source', {})
	prefix = source.get('prefix', '')
	options = []

	for row in sheet_data:
		line_code = row.get('Line Code', '').strip()
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = row.get('Internal Description', '').strip()
		include = row.get('Include', '').strip()

		if not alphanumeric_code.startswith(prefix):
			continue

		suffix = alphanumeric_code[len(prefix):]
		if source.get('suffix') == 'digits' and not suffix.isdigit():
			continue

		options.append({
			'value': line_code,
			'label': internal_description,
			'is_included': include == 'Y'
		})

		if not preselected and include == 'Y' and line_code not in preselected:
			preselected.append(line_code)

	field_schema['options'] = options
	field_schema['preselected'] = preselected
	return field_schema


def build_page_schema_context(page_id, sheet_data, checkbox_data):
	page_schema = get_page_schema(page_id)
	if not page_schema:
		return None

	for index, field_schema in enumerate(page_schema.get('fields', [])):
		if field_schema.get('type') == 'checkbox_group':
			page_schema['fields'][index] = build_schema_checkbox_group(field_schema, sheet_data, checkbox_data)

	return page_schema


def persist_schema_page_submission(page_schema, form_data, checkbox_data):
	for field_schema in page_schema.get('fields', []):
		storage_key = field_schema.get('storage', {}).get('key', field_schema['name'])
		if field_schema.get('type') == 'checkbox_group':
			selected_values = form_data.getlist(field_schema['name'])
			checkbox_data[storage_key] = {'preselected': selected_values if selected_values else []}

	return checkbox_data

# Function to fetch and cache data
def fetch_data():
	if TEST_MODE:
		return deepcopy(mock_sheet_data)

	try:
		print("Fetching fresh data from Google Sheets...")
		sheet = client.open_by_key(spreadsheet_id).worksheet("Sheet1")
		return sheet.get_all_records()
	except Exception as e:
		print(f"Error fetching Google Sheets data: {e}")
		return None
	
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to check if a line code is included (i.e., marked with 'Y')
def is_included(line_code):
	sheet_data = fetch_data()
	for row in sheet_data:
		if row.get('Line Code') == line_code and row.get('Include') == 'Y':
			return True
	return False

# Alphanumeric function - to return only alphanumeric characters from line codes
def to_alphanumeric_code(line_code):
	# Remove all non-alphanumeric characters
	return re.sub(r'[^a-zA-Z0-9]', '', line_code) 

# Function to handle SINGLE dropdown selections (stored in session['data'])
def handle_single_dropdown_session(session, dropdown_key):
	data = session.setdefault('data', {})
	
	selected_value = request.form.get(dropdown_key, "").strip()  # Single value
	
	if selected_value:
		data[dropdown_key] = selected_value
	else:
		data.pop(dropdown_key, None)  # Remove if nothing is selected
		
	session['data'] = data
	
	
# Function to handle MULTIPLE dropdown selections (stored in session['checkbox_data'])
def handle_multi_dropdown_session(checkbox_data, dropdown_key, selected_list):
	selected_values = request.form.getlist(dropdown_key)  # Always returns a list
	
	if selected_values:
		checkbox_data[dropdown_key] = {"preselected": selected_values}
	else:
		checkbox_data[dropdown_key] = {"preselected": []}  # Explicitly store empty
		
	session['checkbox_data'] = checkbox_data
	
# Parent/Child definition helper function
def get_parent_child_map(sheet_data):
	parent_child_map = {}  # Stores {parent: [child1, child2, ...]}
	alphanumeric_to_line = {}  # Maps alphanumeric code -> original line_code
	temp_mapping = {}  # Temporary {alphanumeric_code: [list of children]}
	
	# Step 1: Convert all line codes to alphanumeric and store the mapping
	for row in sheet_data:
		line_code = row.get("Line Code", "").strip()
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Skip empty alphanumeric codes to prevent IndexError
		if not alphanumeric_code:
			continue  # Skip processing this line to prevent errors
		
		# Store both original and alphanumeric versions
		alphanumeric_to_line[alphanumeric_code] = line_code
		
		if alphanumeric_code[-1].isdigit():  # Parent ends in a number
			temp_mapping[alphanumeric_code] = []  
		else:  # Child ends in a letter or special character
			parent_base = alphanumeric_code[:-1]  
			temp_mapping.setdefault(parent_base, []).append(line_code)
		
	# Step 2: Convert alphanumeric map back to full line_code
	for alphanumeric_parent, children in temp_mapping.items():
		if alphanumeric_parent in alphanumeric_to_line:  # Ensure the parent exists
			parent_line_code = alphanumeric_to_line[alphanumeric_parent]
			parent_child_map[parent_line_code] = children  # Store with full `line_code`
		
	return parent_child_map  #  Parent/Child map in **line_code format**

# Float conversion handling 
def to_float(value, default=0.0):
	"""
	Converts a string to a float, handling empty values and errors gracefully.
	- If value is a valid number, returns it as a float.
	- If value is empty or invalid, returns the default (0.0 by default).
	"""
	try:
		return round(float(value), 2)
	except (ValueError, TypeError):
		return default

################################################################################################################################
	
													# Image Processing
	
################################################################################################################################
	
from PIL import Image, ImageOps
import os
from templates import TEMPLATE_COORDINATES, get_layout_definition

def analyze_site_images(upload_path):
	image_meta = []
	for filename in sorted(os.listdir(upload_path)):
		if filename.startswith("img_site_") and allowed_file(filename):
			file_path = os.path.join(upload_path, filename)
			try:
				with Image.open(file_path) as img:
					width, height = img.size
					orientation = 'landscape' if width > height else 'portrait'
					image_meta.append({
						'filename': filename,
						'path': file_path,
						'orientation': orientation,
						'width': width,
						'height': height
					})
			except Exception as e:
				print(f"Error reading {file_path}: {e}")
	return image_meta


def select_templates(image_meta):
	def chunk_images(meta, max_group_size=10):
		return [meta[i:i + max_group_size] for i in range(0, len(meta), max_group_size)]
	
	templates = []
	chunks = chunk_images(image_meta)
	
	for chunk in chunks:
		portrait_count = sum(1 for img in chunk if img['orientation'] == 'portrait')
		landscape_count = sum(1 for img in chunk if img['orientation'] == 'landscape')
		total_count = len(chunk)
		
		matching_templates = [
			key for key in TEMPLATE_COORDINATES
			if key.startswith(f'template_{total_count}-{landscape_count}L{portrait_count}P')
		]
		
		if matching_templates:
			templates.append({
				'templates': matching_templates[:4],
				'remaining': matching_templates[4:],  # for "load more"
				'images': [img['filename'] for img in chunk]
			})
		else:
			print(f"[WARNING] No matching template found for {total_count} images ({landscape_count}L, {portrait_count}P).")
			
	return templates


def compose_template(image_plan, upload_folder, output_basename='final_output'):
	from PIL import Image, ImageOps
	
	canvas_width = 2480  # A4 @ 300dpi
	canvas_height = 3508
	margin = 10  # px
	
	for idx, block in enumerate(image_plan, start=1):
		template_key = block.get('template')
		image_list = block.get('images', [])
		coordinates = get_layout_definition(template_key)
		
		canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
		
		for i, (x, y, w, h) in enumerate(coordinates):
			if i >= len(image_list):
				break
			image_filename = image_list[i]
			image_path = os.path.join(upload_folder, image_filename)
			
			try:
				with Image.open(image_path) as img:
					img = img.convert("RGB")
					target_size = (w - 2 * margin, h - 2 * margin)
					fitted_img = ImageOps.fit(img, target_size, method=Image.LANCZOS)
					canvas.paste(fitted_img, (x + margin, y + margin))
			except Exception as e:
				print(f"[ERROR] Could not process {image_filename}: {e}")
				
		# Save individual page
		filename = f"{output_basename}_{idx}.jpg"
		output_path = os.path.join(upload_folder, filename)
		canvas.save(output_path)
		print(f"[INFO] Saved layout page: {output_path}")
	

################################################################################################################################
		
													# Function to update DESCRIPTION columns
		
################################################################################################################################
		
def update_description_column(**submit_to_description_function):
	if TEST_MODE:
		return []
	
	if not submit_to_description_function:
		print("No manual inputs provided, skipping description update.")
		return []  # Return an empty list to prevent errors in submit()
	
	try:
		# Fetch the sheet data
		sheet_data = fetch_data()
		if not sheet_data:
			print("⚠ ERROR: No data fetched from Google Sheets.")
			return
		description_column_index = 11  # Description column
		dimensions_column_index = 10  # Dimensions column
		cost_column_index = 6  # Cost column
		units_column_index = 7  # Units column
		
		updates = []
		description_column_includes = []
		
		# Map line codes to their corresponding input variables
		# Map line codes to their corresponding input variables
		description_mappings = {
			# Project Details
			'pd1': 'client_address',  
			'pd2': 'Date',  
			'pd4^': 'fire_doors_number',  
			'pd5^': 'non_fire_doors_number',  
			
			# Sliding Doors
			'pd10': 'sliding_door_area',   # Doors / Sliding Door Area  
			
			# Additional Notes
			'an1': 'an1_manual_input',  
			'an2': 'an2_manual_input',  
			'an3': 'an3_manual_input',  
			'an4': 'an4_manual_input',  
			'an5': 'an5_manual_input',  
			'an6': 'an6_manual_input',  
			'an7': 'an7_manual_input',  
			
			# New Build
			'nb1#': 'nb1_manual_input',  
			'nb2#': 'nb2_manual_input',  
			
			# Other Manual Inputs
			'cs0': 'other_council',  
			'er7^': 'other_roofing_description',  
			'dra': 'drainage_other_input',  
			'dw6#': 'other_demolition_option'  
		}
		
		# Dimensions column mappings
		dimensions_mappings = {
			# General Dimensions
			'dm1@': 'dimension_1',  
			'dm2@': 'dimension_2',  
			'dm3@': 'dimension_3',  
			'dm4@': 'dimension_4',  
			'dm5@': 'sliding_door_dimensions',  # Sliding Door Dimensions  
			
			# Lightwell
			'lwx': 'lightwell_dimensions',  
			
			# Wall Heights
			'ew4': 'wall_height_metres',  
			'ew5': 'wall_height_centimetres'  
		}
		
		# Cost column mappings
		cost_mappings = {}
		
		# Explicitly handle predefined cost fields (drainage & demolition)
		direct_cost_values = {'dw6#': 'other_demolition_cost', 'dr4^': 'drainage_other_cost'}
		cost_mappings.update(direct_cost_values)
		
		# Ensure 'iw_fixed_values' exists before looping
		if 'iw_fixed_values' in submit_to_description_function and submit_to_description_function['iw_fixed_values']:
			for key in submit_to_description_function['iw_fixed_values']:
				cost_mappings[key] = 'iw_fixed_values'
						
		# Units column mapping
		units_mappings = {
			# Electrics
			'elkl0': 'kitchen_lights_amount',
			'elkp0': 'kitchen_points_amount',
			'elll0': 'loft_lights_amount',
			'ellp0': 'loft_points_amount'
		}
		
		# Ensure 'iw_sqm_values' exists before looping
		if 'iw_sqm_values' in submit_to_description_function and submit_to_description_function['iw_sqm_values']:
			for key in submit_to_description_function['iw_sqm_values']:
				units_mappings[key] = 'iw_sqm_values'
		
		for row_index, row in enumerate(sheet_data, start=2): 
			line_code = row.get('Line Code', '').strip()
			alphanumeric_code = to_alphanumeric_code(line_code)  			
			
			# Update description column
			if line_code in description_mappings:
				input_value = submit_to_description_function.get(description_mappings[line_code], '').strip()
				if input_value: 
					updates.append({'range': f'K{row_index}', 'values': [[input_value]]})
					description_column_includes.append(line_code)
					
			# Update dimensions column
			if line_code in dimensions_mappings:
				input_value = submit_to_description_function.get(dimensions_mappings[line_code], '').strip()
				if input_value:
					updates.append({'range': f'J{row_index}', 'values': [[input_value]]})
					description_column_includes.append(line_code)
		
			# Update Cost column
			if line_code in cost_mappings:
				cost_dict_name = cost_mappings[line_code]  # Get the mapped dictionary name
				
				retrieved_value = submit_to_description_function.get(cost_dict_name, 'MISSING!')
				
				# If the retrieved value is a dictionary, use it normally
				if isinstance(retrieved_value, dict):
					cost_dict = retrieved_value
					cost_value = to_float(cost_dict.get(line_code, 0))  # Extract correct value
				else:
					cost_value = to_float(retrieved_value)  # If it's a string/float, convert directly
					
				updates.append({'range': f'F{row_index}', 'values': [[cost_value]]})
				
			# Update units column
			if line_code in units_mappings:
				# Ensure units_mappings[line_code] is used correctly
				unit_dict_name = units_mappings[line_code]  # This returns 'iw_sqm_values'
				
				unit_dict = submit_to_description_function.get(unit_dict_name, {})  # Fetch actual dictionary
				unit_value = to_float(unit_dict.get(line_code, 0))  # Extract correct value
				updates.append({'range': f'G{row_index}', 'values': [[unit_value]]})
												
		if updates:
			sheet.batch_update(updates) 
			
		if description_column_includes and len(description_column_includes) > 0:
			update_include_column(description_column_includes)
			
		else:
			print("No updates to send.")
				
		return description_column_includes
	
	except Exception as e:
		print(f" Error updating description columns: {e}")
		
		return [], [] 
		
################################################################################################################################
		
												# Function to Update INCLUDE column 
		
################################################################################################################################
		
def update_include_column(combined_data, description_column_includes=None):
	if TEST_MODE:
		return

	if description_column_includes is None:
		description_column_includes = []  
	
	print(f"DEBUG: Entering update_include_column with combined_data = {combined_data}")
	
	
	row_index = None  # Initialize row_index to avoid errors if it's referenced in an exception
	processed_codes = []
	
	try:
		sheet_data = fetch_data()
		updates = [] 
		
		if not sheet_data:
			return  # Early exit if no data is fetched
		
		# Get parent-child relationships dynamically
		parent_child_map = get_parent_child_map(sheet_data)
		
		# Create an alphanumeric lookup for line codes
		line_code_to_alphanumeric = {row.get('Line Code', '').strip(): to_alphanumeric_code(row.get('Line Code', '')) for row in sheet_data}
		
		for row_index, row in enumerate(sheet_data, start=2):
			line_code = row.get('Line Code', '').strip()  
			include_status = row.get('Include', '') 
			alphanumeric_code = line_code_to_alphanumeric.get(line_code, '')
			
			print(f"DEBUG: Processing Row {row_index} - Line Code: {line_code}, Include: {include_status}")
			
			# 🛠 Confirm `iw` is being found & processed
			if line_code.startswith("iw"):  
				print(f" `iw` Line Code {line_code} is being processed!")
					
			if line_code in description_column_includes and include_status != 'Y':
				print(f" Line Code {line_code} is in Combined Data! Preparing to update...")
				print(f" DEBUG: Marking {line_code} as 'Y' in Include column at row {row_index}")  # Add this log
				
				updates.append({'range': f'E{row_index}', 'values': [['Y']]})
			
			# If it's in `combined_data`, mark it as included
			if line_code in combined_data:
				print(f" DEBUG: Marking {line_code} as 'Y' in Include column at row {row_index}")  # Add this line
				
				if include_status != 'Y':
					updates.append({'range': f'E{row_index}', 'values': [['Y']]})
		
				# Track processed codes
				processed_codes.append(line_code)
				
				# Ensure children are included if parent is selected
				if line_code in parent_child_map:  
					for child_code in parent_child_map[line_code]:  # These are full `line_code`s
						child_row_index = next(
							(i for i, r in enumerate(sheet_data, start=2) if r.get('Line Code', '').strip() == child_code), 
							None
						)
					
						if child_row_index and sheet_data[child_row_index - 2].get('Include', '') != 'Y':  # -2 since we started at 2
							updates.append({'range': f'E{child_row_index}', 'values': [['Y']]})
							processed_codes.append(child_code) 	
							
		processed_codes.extend(combined_data)  
		processed_codes.extend(description_column_includes)
		processed_codes = list(set(processed_codes))
		
		if updates:
			sheet.batch_update(updates) 
		cleanup_include_column(processed_codes)
			
	except Exception as e:
		print(f"Error processing row {row_index if row_index is not None else 'unknown'}: {e}")
		

################################################################################################################################
	
												# CLEANUP INCLUDE COLUMN
	
################################################################################################################################

def cleanup_include_column(processed_codes):
	if TEST_MODE:
		return
	
	try:		
		sheet_data = fetch_data()
		updates = []
		
		if not sheet_data:
			return  # No data, exit early
		
		processed_codes = list(set(processed_codes))  
		
		print(f"DEBUG: Cleanup Running - Processed Codes: {processed_codes}")
		
		for row_index, row in enumerate(sheet_data, start=2):
			line_code = row.get('Line Code', '').strip()  # Keep it in line_code format
			include_status = row.get('Include', '')
			
			# Skip any codes that should remain 'Y'
			if line_code in processed_codes:
				continue  
			
			# Otherwise, mark as 'N'
			if include_status != 'N':
				updates.append({'range': f'E{row_index}', 'values': [['N']]})
				
		if updates:
			sheet.batch_update(updates)
			
	except Exception as e:
		print(f" Error in cleanup_include_column(): {e}")


################################################################################################################################
									
												#TITLE MAPPING DICTIONARY
												
################################################################################################################################
	
	
TITLE_MAPPING = {
	'selected_special_notes': 'Special Notes',
	'selected_building_works': 'Building Works',
	'selected_dw': 'Demolition Works',
	'selected_pp': 'Planning Permission Status',
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
	'selected_frc': 'Further Requirements and Considerations',
	'selected_ab': 'Additional Building Items',
	'selected_sww': 'Schedule of Works (Weeks 1-8)',
	'selected_tww': 'Schedule of Works (Weeks 9-12)',
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
	'selected_bll': 'Boundary Line Wall Requirements (Left)',
	'selected_blr': 'Boundary Line Wall Requirements (Right)',
	'selected_rro': 'Rear Reception Opening Requirements',
	'selected_basement': 'Basement',
	'conservation_status': 'Conservation Area Status',
	'selected_council': 'Local Council',
	'pitched_roof_option': 'Pitched Roof Selection', 
	'selected_iw': 'Internal Wall Options',
	'selected_oe': 'Optional Extras',
	'selected_fw': 'Finishing Works',
	
	# Manual input fields
	'client_address': 'Client Address',
	'Date': 'Date',
	'dm1_manual_input': 'Approximate Extension Size (m)',
	'dm2_manual_input': 'Rear Depth from Original Rear Wall (m)',
	'dm3_manual_input': 'Full Width of Wall (m)',
	'dm4_manual_input': 'Metres Width in Side Return',
	'dm5_manual_input': 'Sliding Door Opening Width (m)', 
	'pd4_manual_input': 'Fire Rated Doors',
	'pd5_manual_input': 'Non-Fire Rated Doors',
	'cs1_manual_input': 'Local Council',
	'pd6_manual_input': 'Number of Kitchen Points',
	'pd7_manual_input': 'Number of Kitchen Lights',
	'pd8_manual_input': 'Number of Loft Points',
	'pd9_manual_input': 'Number of Loft Lights',
	'pd10_manual_input': 'Sliding Door Space',
	'an1_manual_input': 'Additional Notes',  
	'an2_manual_input': 'Neighbours Levels',
	'an3_manual_input': 'Internal to External Levels (Steps)',
	'an4_manual_input': 'Internal Heights',  
	'an5_manual_input': 'Outrigger Stories',
	'an6_manual_input': 'Flush External Walls',
	'an7_manual_input': 'Further Notes',
	'other_council_input': 'Other Council',
	'lightwell_dimensions_input': 'Lightwell Dimensions',
	'drainage_other_input': '',
	
	# Newly added mappings for specific line codes
	'bw4': 'Create a Courtyard/Lightwell',
	'dw4': 'Demolish Garden Wall',
	'ew4': 'Wall Height (Metres)',
	'ew5': 'Wall Height (Centimetres)',
}



################################################################################################################################

													# PAGE - Project Details

################################################################################################################################

@app.route('/', methods=['POST', 'GET'])
def index():
	# Store the current page in the session
	session['last_visited'] = 'index'
	
	if request.method == 'POST':
		data = session.setdefault('data', {})
		
		# Store only non-empty values
		pd1 = request.form.get('client_address', '').strip()
		pd2 = request.form.get('Date', '').strip()
		
		# Convert date to British format (DD/MM/YYYY)
		if pd2:
			try:
				parsed_date = datetime.strptime(pd2, '%Y-%m-%d')
				formatted_date = parsed_date.strftime('%d/%m/%Y')
				data['Date'] = formatted_date
			except ValueError:
				data['Date'] = pd2  # store as-is if invalid
				
		if pd1:
			data['client_address'] = pd1
			
		session['data'] = data
		session.modified = True
		return redirect(url_for('special_notes_page'))
	
	# GET: preload form if data exists
	data = session.get('data', {})
	client_address = data.get('client_address', '')
	raw_date = data.get('Date', '')
	try:
		form_date = datetime.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')
	except ValueError:
		form_date = ''
		
	return render_template(
		'form.html',
		first_page=True,
		next_page='special_notes_page',
		title="Project Details",
		client_address=client_address,
		proposal_date=form_date
	)
	

################################################################################################################################

											# PAGE - SPECIAL NOTES

################################################################################################################################

@app.route('/special_notes_page', methods=['POST', 'GET'])
def special_notes_page():
	# Track navigation
	previous_page = session.get('last_visited', 'index')
	session['last_visited'] = 'special_notes_page'
	
	# Get session storage
	checkbox_data = session.setdefault('checkbox_data', {})
	page_schema = get_page_schema('special_notes_page')
	
	if request.method == 'POST':
		checkbox_data = persist_schema_page_submission(page_schema, request.form, checkbox_data)
		session['checkbox_data'] = checkbox_data
		session.modified = True
		return redirect(url_for('summary_page'))
	
	sheet_data = fetch_data()
	page_schema = build_page_schema_context('special_notes_page', sheet_data, checkbox_data)
				
	return render_template(
		'form.html',
		page_schema=page_schema,
		schema_render_mode='full',
		previous_page=page_schema.get('navigation', {}).get('previous_endpoint', 'index'),
		next_page=page_schema.get('navigation', {}).get('next_endpoint', 'summary_page'),
		title=page_schema.get('title', 'Special Notes')
	)


@app.route('/form_builder_demo', methods=['GET', 'POST'])
def form_builder_demo():
	if request.method == 'POST':
		warnings = update_builder_draft_from_form(request.form)
		flash('Draft schema saved. Changes are active in demo mode.', 'success')
		for warning in warnings:
			flash(warning, 'error')
		return redirect(url_for('form_builder_demo'))

	pages = page_schemas.get('pages', {})
	pricing_rules = get_pricing_rules()
	payment_plan_rules = get_payment_plan_rules()
	template_status = get_template_store_status(template_key=TEMPLATE_STORE_KEY)
	return render_template(
		'form_builder_demo.html',
		pages=pages,
		pricing_rules=pricing_rules,
		payment_plan_rules=payment_plan_rules,
		template_status=template_status,
	)


@app.route('/admin/template_store_status', methods=['GET'])
def template_store_status():
	status = get_template_store_status(template_key=TEMPLATE_STORE_KEY)
	status['template_store_read_enabled'] = TEMPLATE_STORE_READ_ENABLED
	return jsonify(status)


@app.route('/admin/template_store_templates', methods=['GET'])
def template_store_templates():
	overview = get_template_store_overview()
	overview['active_template_key'] = TEMPLATE_STORE_KEY
	return jsonify(overview)


@app.route('/admin/template_clone', methods=['GET'])
def template_clone():
	source_template_key = request.args.get('source_template_key', TEMPLATE_STORE_KEY).strip()
	new_template_key = request.args.get('new_template_key', '').strip()
	new_template_name = request.args.get('new_template_name', '').strip() or None
	scenario_key = request.args.get('scenario_key', 'full_extension').strip() or 'full_extension'
	disabled_pages_raw = request.args.get('disabled_pages', '').strip()
	disabled_pages = [page_id.strip() for page_id in disabled_pages_raw.split(',') if page_id.strip()]

	if not new_template_key:
		return jsonify({'error': 'new_template_key is required'}), 400

	try:
		result = clone_template(
			source_template_key=source_template_key,
			new_template_key=new_template_key,
			new_template_name=new_template_name,
			scenario_key=scenario_key,
			disabled_pages=disabled_pages,
		)
		return jsonify(result)
	except ValueError as exc:
		return jsonify({'error': str(exc)}), 400
	except Exception as exc:
		return jsonify({'error': f'template clone failed: {exc}'}), 500
	
################################################################################################################################

												# PAGE - SUMMARY

################################################################################################################################


@app.route('/summary_page', methods=['POST', 'GET'])
def summary_page():

	previous_page = session.get('last_visited', 'special_notes_page')
	session['last_visited'] = 'summary_page'
	page_schema = get_page_schema('summary_page')

	
	if request.method == 'POST':
		checkbox_data = session.get('checkbox_data', {})
		checkbox_data = persist_schema_page_submission(page_schema, request.form, checkbox_data)
		selected_building_works = checkbox_data.get('selected_building_works', {}).get('preselected', [])
		
		# Ensure empty selection is stored in session
		if not selected_building_works:
			session.setdefault('data', {})['selected_building_works'] = []
		
		# Special Handling for Courtyard Lightwell (bw4)
		lightwell_dimensions_input = request.form.get('lightwell_dimensions_input', '').strip()
		if lightwell_dimensions_input:
			session.setdefault('data', {})['lightwell_dimensions_input'] = lightwell_dimensions_input
			session['lightwell_dimensions_input'] = lightwell_dimensions_input
			session.modified = True
					
		# Handle Boundary Lines
		selected_boundary_lines = request.form.getlist('selected_boundary_lines')  
		
		# Store checkboxes (Wall Construction: Left & Right)
		checkbox_data['selected_bll_checkbox'] = {'preselected': ['bll'] if 'bll' in selected_boundary_lines else []}
		checkbox_data['selected_blr_checkbox'] = {'preselected': ['blr'] if 'blr' in selected_boundary_lines else []}
		
		# Store dropdown selections (Wall Construction: Left & Right)
		handle_multi_dropdown_session(checkbox_data, 'selected_bll', request.form.getlist('selected_bll'))
		handle_multi_dropdown_session(checkbox_data, 'selected_blr', request.form.getlist('selected_blr'))
		
		session.modified = True
		
		# Handle Basement Section
		selected_basement = request.form.getlist('selected_basement')
		session.setdefault('data', {})['selected_basement'] = selected_basement if selected_basement else []
		session['bs1'] = 'Y' if 'bs1' in selected_basement else None
		session['bs2'] = 'Y' if 'bs2' in selected_basement else None
		
		# Handle Planning Permission Status
		selected_pp = request.form.getlist('selected_pp')
		checkbox_data['selected_pp'] = {'preselected': selected_pp}
		if not selected_pp:
			session.setdefault('data', {})['selected_pp'] = []
			
				
		# Handle Conservation Area Section
		conservation_status = request.form.getlist('conservation_status')
		session.setdefault('data', {})['conservation_status'] = conservation_status if conservation_status else []
		session['cs8'] = 'Y' if 'cs8' in conservation_status else None
		session['cs9'] = 'Y' if 'cs9' in conservation_status else None
		
		# Handle Council Section
		selected_council = request.form.getlist('selected_council')
		other_council_input = request.form.get('other_council', '').strip()
		
		# Store selected council, even if it's empty
		session.setdefault('data', {})['selected_council'] = selected_council if selected_council else []
		
		# If 'other' input exists, store it separately
		if other_council_input:
			session.setdefault('data', {})['other_council'] = other_council_input
			
			
		session['checkbox_data'] = checkbox_data
		session.modified = True

		return redirect(url_for('materials_page'))
	
	# Load Data from Google Sheets
	sheet_data = fetch_data()
	page_schema = build_page_schema_context('summary_page', sheet_data, session.get('checkbox_data', {}))
	line_code_descriptions = {row['Line Code']: row['Internal Description'] for row in sheet_data}
	preselected_bw = session.get('checkbox_data', {}).get('selected_building_works', {}).get('preselected', [])	
	preselected_bll = session.get('checkbox_data', {}).get('selected_bll', {}).get('preselected', [])
	preselected_blr = session.get('checkbox_data', {}).get('selected_blr', {}).get('preselected', [])
	preselected_bll_checkbox = session.get('checkbox_data', {}).get('selected_bll_checkbox', {}).get('preselected', [])
	preselected_blr_checkbox = session.get('checkbox_data', {}).get('selected_blr_checkbox', {}).get('preselected', [])
	preselected_basement = session.get('data', {}).get('selected_basement', [])
	lightwell_dimensions_input = session.get('data', {}).get('lightwell_dimensions_input', '')
	preselected_pp = session.get('checkbox_data', {}).get('selected_pp', {}).get('preselected', [])
	preselected_conservation_status = session.get('data', {}).get('conservation_status', [])
	preselected_council = session.get('data', {}).get('selected_council', [])
	other_council = session.get('data', {}).get('other_council', '')
	
	data = {
			"selected_building_works": {"data": {}, "preselected": preselected_bw.copy()},
			"boundary_lines_bll": {"data": {}, "preselected": preselected_bll.copy()},
			"boundary_lines_blr": {"data": {}, "preselected": preselected_blr.copy()},
			"selected_basement": {"data": {}, "preselected": preselected_basement.copy()},
			"selected_pp": {"data": {}, "preselected": preselected_pp.copy()},
			"conservation_status": {"data": {}, "preselected": preselected_conservation_status.copy()},
			"selected_council": {"data": {}, "preselected": preselected_council.copy()},
		
		}
	
	# Lightwell 
	if lightwell_dimensions_input:
		session.setdefault('data', {})['lightwell_dimensions_input'] = lightwell_dimensions_input
		session.modified = True
		
	# Handle 'cs0' separately for storing other_council input
	if other_council:
		session.setdefault('data', {})['other_council'] = other_council  
		session.modified = True  
		
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		if alphanumeric_code.startswith('bw') and alphanumeric_code[2:].isdigit():			
			data["selected_building_works"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			
			if not preselected_bw and include == 'Y' and line_code not in data["selected_building_works"]["preselected"]:
				data["selected_building_works"]["preselected"].append(line_code)

		# Boundary Lines - Left (bll)
		elif alphanumeric_code == 'bll':
			data["boundary_lines_bll"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not session.get('checkbox_data', {}).get('selected_bll_checkbox', {}).get('preselected') \
					and include == 'Y' and line_code not in data["boundary_lines_bll"]["preselected"]:
				data["boundary_lines_bll"]["preselected"].append(line_code)
				
		elif alphanumeric_code in ['bl1', 'bl2', 'bl3', 'bl4', 'bl5', 'bl6']:
			data["boundary_lines_bll"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_bll and include == 'Y' and line_code not in data["boundary_lines_bll"]["preselected"]:
				data["boundary_lines_bll"]["preselected"].append(line_code)
				
		# Boundary Lines - Right (blr)
		elif alphanumeric_code == 'blr':
			data["boundary_lines_blr"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not session.get('checkbox_data', {}).get('selected_blr_checkbox', {}).get('preselected') \
					and include == 'Y' and line_code not in data["boundary_lines_blr"]["preselected"]:
				data["boundary_lines_blr"]["preselected"].append(line_code)
				
		elif alphanumeric_code in ['bl7', 'bl8', 'bl9', 'bl10', 'bl11', 'bl12']:
			data["boundary_lines_blr"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_blr and include == 'Y' and line_code not in data["boundary_lines_blr"]["preselected"]:
				data["boundary_lines_blr"]["preselected"].append(line_code)
				
		# Basement
		elif alphanumeric_code in ['bs1', 'bs2']:
			data["selected_basement"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_basement and include == 'Y' and line_code not in data["selected_basement"]["preselected"]:
				data["selected_basement"]["preselected"].append(line_code)
				
		# Planning Permission
		elif alphanumeric_code.startswith('pp') and line_code != 'ppx':
			data["selected_pp"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_pp and include == 'Y' and line_code not in data["selected_pp"]["preselected"]:
				data["selected_pp"]["preselected"].append(line_code)
				
		elif alphanumeric_code in ['pp2', 'pp3', 'pp4', 'pp5', 'pp6', 'pp7', 'pp8']:
			data["selected_pp"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_pp and include == 'Y' and line_code not in data["selected_pp"]["preselected"]:
				data["selected_pp"]["preselected"].append(line_code)
		
		# Council Section - Conservation Area (cs8, cs9)
		elif alphanumeric_code in ['cs8', 'cs9']:
			data["conservation_status"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			
			if not preselected_conservation_status and include == 'Y':
					data["conservation_status"]["preselected"].append(line_code)
					
		# Council Section
		elif alphanumeric_code in ['cs0', 'cs1', 'cs2', 'cs3', 'cs4', 'cs5', 'cs6', 'cs7']:
			data["selected_council"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}

			if not preselected_council and include == 'Y' and line_code not in data["selected_council"]["preselected"]:
				data["selected_council"]["preselected"].append(line_code)
				
	return render_template(
		'form.html',
		summary_page=True,
		page_schema=page_schema,
		schema_render_mode='partial',
		previous_page=previous_page,
		next_page='materials_page',
		title="Summary Page",
		data=data,  # Pass the entire data dictionary
		other_council=session.get('data', {}).get('other_council', ''),
		preselected_bll_checkbox=preselected_bll_checkbox,
		preselected_blr_checkbox=preselected_blr_checkbox,
		lightwell_dimensions_input=lightwell_dimensions_input,
	)
	

################################################################################################################################
			
												# PAGE - MATERIALS & DETAILS 

################################################################################################################################

@app.route('/materials_page', methods=['POST', 'GET'])
def materials_page():
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('summary_page'))
	session['last_visited'] = 'summary_page'
	
	if request.method == 'POST':
		
		# Retrieve checkbox_data from session or initialize it
		checkbox_data = session.setdefault('checkbox_data', {})
		
		# Handle External Walls (selected_ew)
		selected_ew = request.form.getlist('selected_ew')
		checkbox_data['selected_ew'] = {'preselected': selected_ew}
		
		# Handle Wall Height (Manual Input)
		wall_height_checked = 'ew0' in selected_ew  # Check if 'ew0' is selected
		session.setdefault('data', {})['wall_height_checked'] = wall_height_checked
		
		if wall_height_checked:
			# Validate wall height values before storing in session
			metres = request.form.get('wall_height_metres', '').strip()
			centimetres = request.form.get('wall_height_centimetres', '').strip()
			
			if (not metres or metres.isdigit()) and (not centimetres or centimetres.isdigit()):
				session['data']['wall_height_metres'] = metres
				session['data']['wall_height_centimetres'] = centimetres
			
		# Handle Roofing Options (selected_er)
		selected_er = request.form.getlist('selected_er')
		session.setdefault('data', {})['selected_er'] = selected_er
		
		# Handle Pitched Roof Dropdown Selection
		pitched_roof_option = request.form.getlist('pitched_roof_option')
		if pitched_roof_option:
			session['data']['pitched_roof_option'] = pitched_roof_option
			session.modified = True
		
		# Handle "Other" Roofing Description for 'er7'
		if 'er7^' in pitched_roof_option:  #
			other_roofing_description = request.form.get('other_roofing_description', '').strip()
			if other_roofing_description: 
				session['data']['other_roofing_description'] = other_roofing_description
				session.modified = True

		# Handle Manual Inputs for Internal Doors
		fire_doors_number = request.form.get('fire_doors_number', '').strip()  # pd4
		non_fire_doors_number = request.form.get('non_fire_doors_number', '').strip()  # pd5
		
		# Handle Checkboxes for Internal Doors
		selected_id = request.form.getlist('selected_id')
		session.setdefault('data', {})['selected_id'] = selected_id
			
		# Store Internal Doors Data in Session
		checkbox_data['selected_id'] = {'preselected': selected_id}
		session['data']['fire_doors_number'] = fire_doors_number
		session['data']['non_fire_doors_number'] = non_fire_doors_number 		

		#  Handle Drainage (selected_dr)
		selected_dr = request.form.getlist('selected_dr') 
		checkbox_data['selected_dr'] = {'preselected': selected_dr}
		
		# Handle Drainage "Other" (dr4^ → dwa)
		drainage_other_input = request.form.get('drainage_other_input', '').strip()  
		if drainage_other_input:  
			session['data']['drainage_other_input'] = drainage_other_input
			session.modified = True
			
		# Handle Drainage Other Cost
		drainage_other_cost = request.form.get('drainage_other_cost', '').strip()
		try:
			session.setdefault('data', {})['drainage_other_cost'] = float(drainage_other_cost) if drainage_other_cost else 0.00
		except ValueError:
			session.setdefault('data', {})['drainage_other_cost'] = 0.00  # Fallback if conversion fails
			
		session.modified = True
				
		# Waste and Parking:
		selected_wp = request.form.getlist('selected_wp')
		checkbox_data['selected_wp'] = {'preselected': selected_wp}

		# Ensure session updates are saved
		session['checkbox_data'] = checkbox_data
		session.modified = True
		
		return redirect(url_for('further_requirements_page'))
	
	# Load Data from Google Sheets
	
	sheet_data = fetch_data()
	line_code_descriptions = {row['Line Code']: row['Internal Description'] for row in sheet_data}
	
	# Fetch preselected values from session
	preselected_ew = session.get('checkbox_data', {}).get('selected_ew', {}).get('preselected', [])
	wall_height_metres = session.get('data', {}).get('wall_height_metres', '')
	wall_height_centimetres = session.get('data', {}).get('wall_height_centimetres', '')
	wall_height_checked = session.get('data', {}).get('wall_height_checked', False)
	preselected_er = session.get('data', {}).get('selected_er', [])
	preselected_pitched_roof_option = session.get('data', {}).get('pitched_roof_option', [])
	other_roofing_description = session.get('data', {}).get('other_roofing_description', '')
	preselected_id = session.get('data', {}).get('selected_id', [])
	fire_doors_number = session.get('data', {}).get('fire_doors_number', '')
	non_fire_doors_number = session.get('data', {}).get('non_fire_doors_number', '')
	preselected_dr = session.get('checkbox_data', {}).get('selected_dr', {}).get('preselected', [])
	preselected_wp = session.get('checkbox_data', {}).get('selected_wp', {}).get('preselected', [])
	
	data = {
		"selected_ew": {"data": {}, "preselected": preselected_ew.copy()},
		"selected_er": {"data": {}, "preselected": preselected_er.copy()},
		"pitched_roof_option": {"data": {}, "preselected": preselected_pitched_roof_option.copy()},
		"other_roofing_description": other_roofing_description,
		"selected_dr": {"data": {}, "preselected": preselected_dr.copy()},
		"selected_wp": {"data": {}, "preselected": preselected_wp.copy()},
		"drainage_other_input": session.get('data', {}).get('drainage_other_input', ''),
		"drainage_other_cost": session.get('data', {}).get('drainage_other_cost', '0.00'),
		"wall_height_metres": wall_height_metres,
		"wall_height_centimetres": wall_height_centimetres,
		"wall_height_checked": wall_height_checked,
		"selected_id": {"data": {}, "preselected": preselected_id.copy()},
		"fire_doors_number": fire_doors_number,
		"non_fire_doors_number": non_fire_doors_number,
	}
	
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		#  Populate External Walls Data
		if alphanumeric_code.startswith('ew') and alphanumeric_code[-1].isdigit():
			data["selected_ew"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if not preselected_ew and include == 'Y' and line_code not in data["selected_ew"]["preselected"]:
				data["selected_ew"]["preselected"].append(line_code)
					
		#  Populate External Roof Data
		elif alphanumeric_code.startswith('er') and alphanumeric_code[-1].isdigit():
			data["selected_er"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_er:
				data["selected_er"]["preselected"].append(line_code)	
		
		# Pitched Roof Options (er4–er7)
		if alphanumeric_code in ['er4', 'er5', 'er6', 'er7']:
			data["pitched_roof_option"]["data"][line_code] = {
				"description": internal_description or "Unknown Roofing Type",
				"is_included": include == 'Y'
			}
			if line_code in preselected_pitched_roof_option:
				data["pitched_roof_option"]["preselected"].append(line_code)
	
		# Internal Doors
		elif alphanumeric_code.startswith('id') and alphanumeric_code[-1].isdigit():
			data["selected_id"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_id:
				data["selected_id"]["preselected"].append(line_code)
		
		# Drainage
		elif alphanumeric_code.startswith('dr') and alphanumeric_code[-1].isdigit():  
			data["selected_dr"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_dr and line_code not in data["selected_dr"]["preselected"]:
				data["selected_dr"]["preselected"].append(line_code)
				
		# Waste & Parking:
		elif alphanumeric_code.startswith('wp') and alphanumeric_code[-1].isdigit():
			data["selected_wp"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_wp and line_code not in data["selected_wp"]["preselected"]:
				data["selected_wp"]["preselected"].append(line_code)
				
				
	# Handle Wall Height (`ew4` and `ew5`)
	if 'ew0' in preselected_ew:
		if wall_height_metres and 'ew4' not in data["selected_ew"]["preselected"]:
			data["selected_ew"]["preselected"].append('ew4')
		if wall_height_centimetres and 'ew5' not in data["selected_ew"]["preselected"]:
			data["selected_ew"]["preselected"].append('ew5')
	
		
	return render_template(
		'form.html',
		materials_page=True,
		previous_page=previous_page,
		next_page='further_requirements_page',
		title="Materials and Details",
		data=data,
		wall_height_metres=data.get('wall_height_metres', ''),
		wall_height_centimetres=data.get('wall_height_centimetres', ''),
		fire_doors_number=data.get('fire_doors_number', ''),
		non_fire_doors_number=data.get('non_fire_doors_number', '')
	)
	
################################################################################################################################

							# PAGE - Further Requirements & Considerations

################################################################################################################################

@app.route('/further_requirements_page', methods=['POST', 'GET'])
def further_requirements_page():
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('materials_page'))
	session['last_visited'] = 'further_requirements_page'
	
	if request.method == 'POST':
		
		checkbox_data = session.setdefault('checkbox_data', {})
		
		# Further requirements
		selected_frc = [note.strip() for note in request.form.getlist('selected_frc') if note.strip()]
		checkbox_data['selected_frc'] = {'preselected': selected_frc}
		
		# Other Demolition Works
		selected_dw = [note.strip() for note in request.form.getlist('selected_dw') if note.strip()]
		checkbox_data['selected_dw'] = {'preselected': selected_dw}
		
		#Floor Structure
		selected_fs = request.form.getlist('selected_fs')
		checkbox_data['selected_fs'] = {'preselected': selected_fs}
		
		# Glass Valley
		selected_gv = request.form.getlist('selected_gv')
		checkbox_data['selected_gv'] = {'preselected': selected_gv}
		
		# Other Demolition Works OPtions
		other_demolition_option = request.form.get('other_demolition_option', '').strip()
		other_demolition_cost = request.form.get('other_demolition_cost', '').strip()
		
		# Rear Reception Opening
		selected_rro = request.form.getlist('selected_rro')
		checkbox_data['selected_rro'] = {'preselected': selected_rro}
		
		# Inner Walls
		selected_iw = request.form.getlist('selected_iw')
		checkbox_data['selected_iw'] = {'preselected': selected_iw}
		
		# Internal Wall Inputs (Square Meterage & Fixed Cost)
		iw_sqm_values = {}
		iw_fixed_values = {}
		
		iw_input_type_values = {}
		for key in selected_iw:
			input_type = request.form.get(f'iwType_{key}', '').strip()
			if input_type:
				iw_input_type_values[key] = input_type
		session['data']['iw_input_type_values'] = iw_input_type_values
		
		for key in selected_iw:
			sqm_value = request.form.get(f'iwSqmValue_{key}', '').strip()
			fixed_value = request.form.get(f'iwFixedValue_{key}', '').strip()
			if sqm_value:
				iw_sqm_values[key] = sqm_value
			if fixed_value:
				iw_fixed_values[key] = fixed_value
				
		
		session.setdefault('data', {})['selected_dw'] = selected_dw
		session['data']['iw_sqm_values'] = iw_sqm_values
		session['data']['iw_fixed_values'] = iw_fixed_values
		
		# Only store "Other Demolition" inputs if dw6# is selected
		if 'dw6#' in selected_dw:
			session['data']['other_demolition_option'] = request.form.get('other_demolition_option', '').strip()
			
			try:
				session['data']['other_demolition_cost'] = float(request.form.get('other_demolition_cost', '').strip() or 0)
			except ValueError:
				session['data']['other_demolition_cost'] = 0  # Fallback if conversion fails
		else:
			# Remove fields if dw6# is NOT selected
			session['data'].pop('other_demolition_option', None)
			session['data'].pop('other_demolition_cost', None)
			
		session.modified = True  
		return redirect(url_for('additional_building_work_page'))
	
	# Fetch preselected values from session
	preselected_frc = session.get('checkbox_data', {}).get('selected_frc', {}).get('preselected', [])
	preselected_dw = session.get('checkbox_data', {}).get('selected_dw', {}).get('preselected', [])
	preselected_fs = session.get('checkbox_data', {}).get('selected_fs', {}).get('preselected', [])
	preselected_gv = session.get('checkbox_data', {}).get('selected_gv', {}).get('preselected', [])
	preselected_rro = session.get('checkbox_data', {}).get('selected_rro', {}).get('preselected', [])
	preselected_iw = session.get('checkbox_data', {}).get('selected_iw', {}).get('preselected', [])
	
	# Initialize the `data` structure for this page
	data = {
		"selected_frc": {"data": {}, "preselected": preselected_frc.copy()},
		"selected_dw": {"data": {}, "preselected": preselected_dw.copy()},
		"other_demolition_option": session.get('data', {}).get('other_demolition_option', ''),
		"other_demolition_cost": session.get('data', {}).get('other_demolition_cost', ''),
		"selected_fs": {"data": {}, "preselected": preselected_fs.copy()}, 
		"selected_gv": {"data": {}, "preselected": preselected_gv.copy()}, 
		"selected_rro": {"data": {}, "preselected": preselected_rro.copy()},
		"selected_iw": {"data": {}, "preselected": preselected_iw.copy()},
		"iw_sqm_values": session.get('data', {}).get('iw_sqm_values', {}),  
		"iw_fixed_values": session.get('data', {}).get('iw_fixed_values', {}),
		"iw_input_type_values": session.get('data', {}).get('iw_input_type_values', {}),
		
	}
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	line_code_descriptions = {row['Line Code']: row['Internal Description'] for row in sheet_data}
	
	
	# Filter the relevant rows based on 'frc' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '')
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = row.get('Internal Description', '')
		include = row.get('Include', '')
		
		if alphanumeric_code.startswith('frc') and alphanumeric_code[-1].isdigit():  
			data["selected_frc"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_frc and line_code not in data ["selected_frc"]["preselected"]:
				data["selected_frc"]["preselected"].append(line_code)
		
		# Demolition Works
		elif alphanumeric_code.startswith('dw') and line_code not in ['dw4#']:
			data["selected_dw"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_dw and line_code not in data ["selected_dw"]["preselected"]:
				data["selected_dw"]["preselected"].append(line_code)
				
		# Demolition Works - Standalone Checkboxes (dw4#, dw7, dw8, dw9, dw10)
		elif alphanumeric_code.startswith('dw') and line_code in ['dw4#', 'dw7', 'dw8', 'dw9', 'dw10']:  
			data["selected_dw"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_dw and line_code not in data["selected_dw"]["preselected"]:
					data["selected_dw"]["preselected"].append(line_code)
	
		# Floor Structure Data
		elif alphanumeric_code.startswith('fs') and alphanumeric_code[-1].isdigit():  
			data["selected_fs"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_fs and line_code not in data["selected_fs"]["preselected"]:
					data["selected_fs"]["preselected"].append(line_code)
				
		# Handle Glass Valley (gv)
		elif alphanumeric_code.startswith('gv') and alphanumeric_code[-1].isdigit():  
			data["selected_gv"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_gv and line_code not in data["selected_gv"]["preselected"]:
					data["selected_gv"]["preselected"].append(line_code)
				
				
		# Rear Reception Opening (RRO)
		elif alphanumeric_code.startswith('rro') and alphanumeric_code[-1].isdigit():
			data["selected_rro"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_rro and line_code not in data["selected_rro"]["preselected"]:
					data["selected_rro"]["preselected"].append(line_code)
		
		# Internal Walls (`iw1# - iw5#`)
		elif alphanumeric_code.startswith('iw') and alphanumeric_code[-1].isdigit():
			data["selected_iw"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_iw and line_code not in data["selected_iw"]["preselected"]:
					data["selected_iw"]["preselected"].append(line_code)
	
	# Render the form with the updated data structure
	return render_template(
		'form.html',
		further_requirements_page=True,
		previous_page=previous_page,
		next_page='additional_building_work_page',
		title="Further Requirements & Considerations",
		data=data,
		iw_sqm_values=data.get('iw_sqm_values', {}),
		iw_fixed_values=data.get('iw_fixed_values', {})
	)	

################################################################################################################################

												# PAGE - Additional Building Work
												
################################################################################################################################

@app.route('/additional_building_work_page', methods=['POST', 'GET'])
def additional_building_work_page():
	# Store the current page in the session
	previous_page = session.get('last_visited', 'further_requirements_page')  # Update this placeholder when renaming other pages
	session['last_visited'] = 'additional_building_work_page'
	
	if request.method == 'POST':
		
		checkbox_data = session.setdefault('checkbox_data', {})
		
		# Store selected checkboxes into session
		selected_ab = [note.strip() for note in request.form.getlist('selected_ab') if note.strip()]
		checkbox_data['selected_ab'] = {'preselected': selected_ab}

		session.modified = True  
			
		return redirect(url_for('additional_costs_page'))  # Update this placeholder when renaming other pages
	
	# Load data from Google Sheets
	sheet_data = fetch_data()
	preselected_ab = session.get('checkbox_data', {}).get('selected_ab', {}).get('preselected', [])
	
	data = {
		"selected_ab": {"data": {}, "preselected": preselected_ab.copy()},
		}
	
	# Filter the relevant rows based on 'ab' prefix
	for row in sheet_data:
		line_code = row.get('Line Code', '').strip()
		internal_description = row.get('Internal Description', '').strip()
		include = row.get('Include', '').strip()
		
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		if alphanumeric_code.startswith('ab') and alphanumeric_code[-1].isdigit():
			data["selected_ab"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_ab and line_code not in data["selected_ab"]["preselected"]:
					data["selected_ab"]["preselected"].append(line_code)
				
				
	return render_template(
		'form.html',
		additional_building_work_page=True,
		previous_page=previous_page,
		next_page='additional_costs_page',  # Update this placeholder when renaming other pages
		title="Additional Building Works",
		data=data
	)
	
################################################################################################################################

												# PAGE - Additional Costs
												
################################################################################################################################
												
												
@app.route('/additional_costs_page', methods=['POST', 'GET'])
def additional_costs_page():
	# Store the current page in the session
	previous_page = session.get('last_visited', 'further_requirements_page')
	session['last_visited'] = 'additional_costs_page'
	
	if request.method == 'POST':
		
		checkbox_data = session.setdefault('checkbox_data', {})
		
		# Electrics: Kitchen toggle
		selected_kitchen_el = [note.strip() for note in request.form.getlist('selected_kitchen_el') if note.strip()]
		checkbox_data['selected_kitchen_el'] = {'preselected': selected_kitchen_el}
		
		# Electrics: Loft toggle
		selected_loft_el = [note.strip() for note in request.form.getlist('selected_loft_el') if note.strip()]
		checkbox_data['selected_loft_el'] = {'preselected': selected_loft_el}
		
		# Dropdown selections
		selected_kitchen_option = request.form.get('selected_kitchen_option', '').strip()
		selected_loft_option = request.form.get('selected_loft_option', '').strip()
		session.setdefault('data', {})['selected_kitchen_option'] = selected_kitchen_option
		session['data']['selected_loft_option'] = selected_loft_option
		
		# Manual inputs
		kitchen_lights_amount = request.form.get('elkl0_amount', '').strip()
		kitchen_points_amount = request.form.get('elkp0_amount', '').strip()
		loft_lights_amount = request.form.get('elll0_amount', '').strip()
		loft_points_amount = request.form.get('ellp0_amount', '').strip()
		
		try:
			kitchen_lights = int(kitchen_lights_amount or 0)
			kitchen_points = int(kitchen_points_amount or 0)
			loft_lights = int(loft_lights_amount or 0)
			loft_points = int(loft_points_amount or 0)
		except ValueError:
			kitchen_lights = kitchen_points = loft_lights = loft_points = 0
			
		pricing_rules = get_pricing_rules()
		kitchen_other_cost = round(
			(kitchen_lights * pricing_rules['kitchen_light_rate']) + (kitchen_points * pricing_rules['kitchen_point_rate']),
			pricing_rules['rounding_precision']
		)
		loft_other_cost = round(
			(loft_lights * pricing_rules['loft_light_rate']) + (loft_points * pricing_rules['loft_point_rate']),
			pricing_rules['rounding_precision']
		)
		
		# Conditional session storage
		if selected_kitchen_option == 'elk0':
			session['data']['elkl0_amount'] = kitchen_lights
			session['data']['elkp0_amount'] = kitchen_points
			session['data']['elk0_cost'] = kitchen_other_cost
		else:
			session['data'].pop('elkl0_amount', None)
			session['data'].pop('elkp0_amount', None)
			session['data'].pop('elk0_cost', None)
			
		if selected_loft_option == 'ell0':
			session['data']['elll0_amount'] = loft_lights
			session['data']['ellp0_amount'] = loft_points
			session['data']['ell0_cost'] = loft_other_cost
		else:
			session['data'].pop('elll0_amount', None)
			session['data'].pop('ellp0_amount', None)
			session['data'].pop('ell0_cost', None)
			
		# Skylights
		selected_sk = [note.strip() for note in request.form.getlist('selected_sk') if note.strip()]
		checkbox_data['selected_sk'] = {'preselected': selected_sk}
		
		# Velux Windows
		selected_vl = [note.strip() for note in request.form.getlist('selected_vl') if note.strip()]
		checkbox_data['selected_vl'] = {'preselected': selected_vl}
		
		# Aluminium Capping 
		selected_ac = [note.strip() for note in request.form.getlist('selected_ac') if note.strip()]
		checkbox_data['selected_ac'] = {'preselected': selected_ac}

		# Store selected checkboxes into session
		selected_pl = request.form.getlist('selected_pl') # plumbing
		
		# Sliding doors:
		selected_sd = request.form.get('selected_sd', '').strip()
		session.setdefault('data', {})['selected_sd'] = selected_sd if selected_sd else ''
		
		session['data']['pd10_manual_input'] = request.form.get('pd10_manual_input', '').strip()
		
		# Ensure session structure exists
		checkbox_data['selected_pl'] = {'preselected': selected_pl}
			
		#  Store manual inputs & computed costs (if "Other" selected)
		if selected_kitchen_option == 'elk0':
			session['data']['elkl0_amount'] = kitchen_lights_amount
			session['data']['elkp0_amount'] = kitchen_points_amount
			session['data']['elk0_cost'] = kitchen_other_cost
		else:
			session.get('data', {}).pop('elkl0_amount', None)
			session.get('data', {}).pop('elkp0_amount', None)
			session.get('data', {}).pop('elk0_cost', None)
			
		if selected_loft_option == 'ell0':
			session['data']['elll0_amount'] = loft_lights_amount
			session['data']['ellp0_amount'] = loft_points_amount
			session['data']['ell0_cost'] = loft_other_cost
		else:
			session.get('data', {}).pop('elll0_amount', None)
			session.get('data', {}).pop('ellp0_amount', None)
			session.get('data', {}).pop('ell0_cost', None)

		additional_costs_subtotal = round(kitchen_other_cost + loft_other_cost, pricing_rules['rounding_precision'])
		session['data']['additional_costs_subtotal'] = additional_costs_subtotal
		session['data']['pricing_rules_used'] = pricing_rules
		session['data']['payment_plan_preview'] = calculate_payment_plan(additional_costs_subtotal, get_payment_plan_rules())
			
		session.modified = True  
		return redirect(url_for('optional_extras_page'))
	
	# Fetch preselected values from session
	preselected_kitchen_el = session.get('checkbox_data', {}).get('selected_kitchen_el', {}).get('preselected', [])
	preselected_loft_el = session.get('checkbox_data', {}).get('selected_loft_el', {}).get('preselected', [])
	preselected_sk = session.get('checkbox_data', {}).get('selected_sk', {}).get('preselected', [])
	preselected_vl = session.get('checkbox_data', {}).get('selected_vl', {}).get('preselected', [])
	preselected_ac = session.get('checkbox_data', {}).get('selected_ac', {}).get('preselected', [])
	selected_sd = session.get("data", {}).get("selected_sd", "")
	
	# Load data from Google Sheets
	sheet_data = fetch_data() or [] 
	
	# Initialize the `data` structure for this page
	data = {
		"selected_sd": {"data": {}, "preselected": [selected_sd] if selected_sd else []},
		"selected_ac": {"data": {}, "preselected": preselected_ac.copy()},
		"selected_vl": {"data": {}, "preselected": preselected_vl.copy()},
		"selected_sk": {"data": {}, "preselected": preselected_sk.copy()},
		"selected_kitchen_el": {"data": {}, "preselected": preselected_kitchen_el.copy()},
		"selected_loft_el": {"data": {}, "preselected": preselected_loft_el.copy()},
		"selected_kitchen_option": session.get('data', {}).get('selected_kitchen_option', ''),
		"selected_loft_option": session.get('data', {}).get('selected_loft_option', ''),
		"elkl0_amount": session.get('data', {}).get('elkl0_amount', 0),
		"elkp0_amount": session.get('data', {}).get('elkp0_amount', 0),
		"elll0_amount": session.get('data', {}).get('elll0_amount', 0),
		"ellp0_amount": session.get('data', {}).get('ellp0_amount', 0),
		"pd10_manual_input": session.get('data', {}).get('pd10_manual_input', ''),
		"selected_pl": {"data": {}, "preselected": []},
	}
	
	# Sliding Door dropdown options
	data["selected_sd"]["data"] = {
		row["Line Code"]: {"line_code": row["Line Code"], "description": row["Internal Description"]}
		for row in sheet_data if row["Line Code"].startswith("sd")
	}
	
	# Electrics dropdown options
	data["selected_kitchen_option_data"] = {
		row["Line Code"]: {"line_code": row["Line Code"], "description": row["Internal Description"]}
		for row in sheet_data if row["Line Code"].startswith("elk")
	}

	data["selected_loft_option_data"] = {
		row["Line Code"]: {"line_code": row["Line Code"], "description": row["Internal Description"]}
		for row in sheet_data if row["Line Code"].startswith("ell")
	}
	
	line_code_descriptions = {row['Line Code']: row['Internal Description'] for row in sheet_data}

	# Filter relevant rows based on prefixes
	for row in sheet_data:
		line_code = str(row.get("Line Code", "")).strip()
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = str(row.get("Internal Description", "")).strip()
		include = row.get("Include", '')
		
		
		# Kitchen Electrics
		if alphanumeric_code.startswith('elk') and alphanumeric_code[-1].isdigit():
			data["selected_kitchen_el"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_kitchen_el and line_code not in data["selected_kitchen_el"]["preselected"]:
				data["selected_kitchen_el"]["preselected"].append(line_code)
				
		# Loft Electrics
		elif alphanumeric_code.startswith('ell') and alphanumeric_code[-1].isdigit():
			data["selected_loft_el"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_loft_el and line_code not in data["selected_loft_el"]["preselected"]:
				data["selected_loft_el"]["preselected"].append(line_code)
				
		elif alphanumeric_code.startswith('pl') and alphanumeric_code[-1].isdigit():
			data["selected_pl"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if include == 'Y':
				data["selected_pl"]["preselected"].append(line_code)
				
		elif alphanumeric_code.startswith('sk') and alphanumeric_code[-1].isdigit():
			data["selected_sk"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_sk and line_code not in data["selected_sk"]["preselected"]:
				data["selected_sk"]["preselected"].append(line_code)

		elif alphanumeric_code.startswith('vl') and alphanumeric_code[-1].isdigit():
			data["selected_vl"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_vl and line_code not in data["selected_vl"]["preselected"]:
				data["selected_vl"]["preselected"].append(line_code)
				
		elif alphanumeric_code.startswith('ac') and alphanumeric_code[-1].isdigit():
			data["selected_ac"]["data"][line_code] = {"description": internal_description, "is_included": include == 'Y'}
			if line_code in preselected_ac and line_code not in data["selected_ac"]["preselected"]:
				data["selected_ac"]["preselected"].append(line_code)
				
		if alphanumeric_code.startswith("sd") and alphanumeric_code != "sd_total#" and line_code:
			data["selected_sd"]["data"][line_code] = {
				"line_code": line_code,
				"description": internal_description 
			}
	
				
	return render_template(
		'form.html',
		additional_costs_page=True,
		previous_page=previous_page,
		next_page='optional_extras_page',
		title="Additional Costs",
		data=data,
		selected_kitchen_option_data=data.get("selected_kitchen_option_data", {}),
		selected_loft_option_data=data.get("selected_loft_option_data", {}),
		pd10_label="Specify sliding door width (mm):" 
	)
	
	
################################################################################################################################

												# Optional Extras & Finishing Works.
														
################################################################################################################################
														
# Combined page route - Optional Extras & Finishing Works
@app.route('/optional_extras_page', methods=['GET', 'POST'])
def optional_extras_page():
	
	# Store the current page in the session
	previous_page = session.get('last_visited', url_for('additional_costs_page'))
	session['last_visited'] = 'optional_extras_page'
	
	if request.method == 'POST':
		
		checkbox_data = session.setdefault('checkbox_data', {})
		
		#Optional Extras - to be updated
		selected_oe = request.form.getlist('selected_oe')
		checkbox_data['selected_oe'] = {'preselected': selected_oe}
		
		#Handle dropdown for chimney breast (optional extras)
		chimney_breast_option = request.form.get('chimney_breast_option', '').strip()
		session.setdefault('data', {})['chimney_breast_option'] = chimney_breast_option
		
		#Finishing Works: 
		selected_fw = [note.strip() for note in request.form.getlist('selected_fw') if note.strip()]
		checkbox_data['selected_fw'] = {'preselected': selected_fw}
		
		selected_fw_option = request.form.get('selected_fw_option', '').strip()
		selected_fw_utility_option = request.form.get('selected_fw_utility_option', '').strip()
		selected_fw_bathroom_option = request.form.get('selected_fw_bathroom_option', '').strip()
		selected_fw_rear_half_option = request.form.get('selected_fw_rear_half_option', '').strip()
		selected_fw_rear_full_option = request.form.get('selected_fw_rear_full_option', '').strip()
		
		session.setdefault('data', {})['selected_fw_option'] = selected_fw_option
		session['data']['selected_fw_utility_option'] = selected_fw_utility_option
		session['data']['selected_fw_bathroom_option'] = selected_fw_bathroom_option
		session['data']['selected_fw_rear_half_option'] = selected_fw_rear_half_option
		session['data']['selected_fw_rear_full_option'] = selected_fw_rear_full_option
		
		
		session.modified = True
		return redirect(url_for('image_upload_page'))  # Now goes to image upload before review
	
	
	# Fetch preselected values from session
	preselected_fw = session.get('checkbox_data', {}).get('selected_fw', {}).get('preselected', [])
	
	# Load and filter sheet data
	sheet_data = fetch_data() or []
	
	data = {
		"selected_fw": {"data": {}, "preselected": preselected_fw.copy()},
		"selected_oe": {"data": {}, "preselected": session.get('checkbox_data', {}).get('selected_oe', {}).get('preselected', [])},
		"chimney_breast_option": session.get('data', {}).get('chimney_breast_option', ''),
		"selected_fw_option": session.get('data', {}).get('selected_fw_option', ''),
		"selected_fw_utility_option": session.get('data', {}).get('selected_fw_utility_option', ''),
		"selected_fw_bathroom_option": session.get('data', {}).get('selected_fw_bathroom_option', ''),
		"selected_fw_rear_half_option": session.get('data', {}).get('selected_fw_rear_half_option', ''),
		"selected_fw_rear_full_option": session.get('data', {}).get('selected_fw_rear_full_option', ''),
	}
	
	
	for row in sheet_data:
		line_code = row.get('Line Code', '').strip()
		alphanumeric_code = to_alphanumeric_code(line_code)
		internal_description = row.get('Internal Description', '').strip()
		include = row.get('Include', '').strip()
		
		# Optional Extras: codes starting 'oe' 
		if alphanumeric_code.startswith('oe') and alphanumeric_code[2:].isdigit():
			data["selected_oe"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if include == 'Y' and line_code not in data["selected_oe"]["preselected"]:
				data["selected_oe"]["preselected"].append(line_code)
				
		# Finishing Works: codes starting 'fw'
		elif alphanumeric_code.startswith('fw') and alphanumeric_code[2:].isdigit():
			data["selected_fw"]["data"][line_code] = {
				"description": internal_description,
				"is_included": include == 'Y'
			}
			if line_code in preselected_fw and line_code not in data["selected_fw"]["preselected"]:
					data["selected_fw"]["preselected"].append(line_code)
				
	# Render combined form
	return render_template(
		'form.html',
		optional_extras_page=True,
		previous_page=previous_page,
		next_page='image_upload_page',
		title="Optional Extras & Finishing Works",
		data=data
	)
														
################################################################################################################################

														# Image Upload
														
################################################################################################################################

@app.route('/image_upload_page', methods=['GET', 'POST'])
def image_upload_page():
	session['last_visited'] = 'image_upload_page'
	
	project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
	safe_title = secure_filename(project_title)
	project_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_title)
	os.makedirs(project_folder, exist_ok=True)
		
	uploaded_images = session.get('uploaded_images', {})
	
	files = request.files.getlist('site_images')
	action = request.form.get('action')
	selected_images = request.form.getlist('selected_images')
	selected_template_key = request.form.get('selected_template')
	open_accordion = request.form.get('open_accordion')	
		
	index_offset = len([f for f in os.listdir(project_folder) if f.startswith('img_site_')])
	
	# Reset session and file state if requested
	if request.method == 'POST' and request.form.get('reset_session'):
		for f in os.listdir(project_folder):
			path = os.path.join(project_folder, f)
			if os.path.isfile(path):
				os.remove(path)
		session.pop('uploaded_images', None)
		session.pop('chosen_template', None)
		session.pop('site_image_plan', None)
		session.modified = True
		flash("Session and project folder fully reset.", "info")
		return redirect(url_for('image_upload_page'))
	
	# Delete selected images
	if action == 'delete' and selected_images:
		for filename in selected_images:
			path = os.path.join(project_folder, filename)
			if os.path.exists(path):
				os.remove(path)
				uploaded_images.pop(filename, None)
		session['uploaded_images'] = uploaded_images
		session.modified = True

	# Handle alternate layout selection preview
	if selected_template_key:
		session['chosen_template'] = selected_template_key
		if session.get('site_image_plan'):
			image_plan = [{
				'template': selected_template_key,
				'images': session['site_image_plan'][0]['images']
			}]
			compose_template(image_plan, project_folder)
			from time import time
			preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') + f'?v={int(time())}'
			uploaded_images['final_output_1.jpg'] = preview_url
			session['uploaded_images'] = uploaded_images
			session.modified = True
			
	# Re-analyze and recompose after deletion
	image_meta = analyze_site_images(project_folder)
	if image_meta:
		template_plan = select_templates(image_meta)
		session['site_image_plan'] = template_plan
		
		# Ensure chosen template is valid
		if session.get('chosen_template') not in template_plan[0]['templates']:
			session['chosen_template'] = template_plan[0]['templates'][0]
				
		for key in list(uploaded_images.keys()):
			if key.startswith('final_output_') and key.endswith('.jpg'):
				uploaded_images.pop(key, None)
				
		if session.get('chosen_template'):
			image_plan = [{
				'template': session['chosen_template'],
				'images': template_plan[0]['images']
			}]
			compose_template(image_plan, project_folder)
			from time import time
			preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') + f'?v={int(time())}'
			uploaded_images['final_output_1.jpg'] = preview_url
			session['uploaded_images'] = uploaded_images
			session.modified = True
				
	
	# Upload new files
	if files and any(file.filename for file in files):
		for i, file in enumerate(files, start=1):
			if file and allowed_file(file.filename):
				filename = f"img_site_{index_offset + i}.jpg"
				save_path = os.path.join(project_folder, filename)
				file.save(save_path)
				with Image.open(save_path) as img:
					img.convert("RGB").save(save_path, format='JPEG', optimize=True, quality=85)
				uploaded_images[filename] = url_for('static', filename=f'uploads/{safe_title}/{filename}')
				
		uploaded_count = len(files)
		if uploaded_count > 0:
			flash(f"{uploaded_count} image{'s' if uploaded_count != 1 else ''} uploaded successfully.", "success")
			
		# Flash message for "Include in Layout"
		if action == 'include' and selected_images:
			flash(f"{len(selected_images)} image{'s' if len(selected_images) != 1 else ''} selected for layout.", "success")
				
		# Clear layout
		if request.form.get('clear_layout'):
			for f in os.listdir(project_folder):
				if f.startswith('final_output_') and f.endswith('.jpg'):
					os.remove(os.path.join(project_folder, f))
					uploaded_images.pop(f, None)
			session['uploaded_images'] = uploaded_images
			session.modified = True
			return redirect(url_for('image_upload_page'))
	
		# Store selected template
		if selected_template_key:
			session['chosen_template'] = selected_template_key
			
		session['uploaded_images'] = uploaded_images
		session.modified = True
		
		# Recompose layout immediately when alternate template is selected
		if session.get('site_image_plan'):
			image_plan = [{
				'template': selected_template_key,
				'images': session['site_image_plan'][0]['images']
			}]
			compose_template(image_plan, project_folder)
			from time import time
			preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') + f'?v={int(time())}'
			uploaded_images['final_output_1.jpg'] = preview_url
			session['uploaded_images'] = uploaded_images
			session.modified = True
			
		# Analyze current images
		image_meta = analyze_site_images(project_folder)
		if not image_meta:
			flash("No valid images found for layout.", "danger")
			return render_template('image_upload.html', uploaded_images=uploaded_images)
		
		# Generate layout plan and store
		template_plan = select_templates(image_meta)
		session['site_image_plan'] = template_plan
		
		# Default selection
		if not session.get('chosen_template') and template_plan and template_plan[0]['templates']:
			session['chosen_template'] = template_plan[0]['templates'][0]
			
		# Ensure chosen template is still valid
		if session.get('chosen_template') not in template_plan[0]['templates']:
			session['chosen_template'] = template_plan[0]['templates'][0]
			
		# Remove old preview pages from memory
		for key in list(uploaded_images.keys()):
			if key.startswith('final_output_') and key.endswith('.jpg'):
				uploaded_images.pop(key, None)
			
		# Compose updated preview(s)
		if session.get('chosen_template'):
			image_plan = [{
				'template': session['chosen_template'],
				'images': template_plan[0]['images']
			}]
			compose_template(image_plan, project_folder)
			
			from time import time
			preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') + f'?v={int(time())}'
			uploaded_images['final_output_1.jpg'] = preview_url
			session['uploaded_images'] = uploaded_images
			session.modified = True
				
	return render_template(
		'image_upload.html',  # 
		image_upload_page=True,
		previous_page='optional_extras_page',
		next_page='review',
		open_accordion=open_accordion,
		title="Upload Quote-Specific Images",
		uploaded_images=uploaded_images,
		template_plan=session.get('site_image_plan', [])
	)
	
	

################################################################################################################################

														# Review Page

################################################################################################################################

@app.route('/review', methods=['GET', 'POST'])
def review():
	if request.method == 'POST':
		return redirect(url_for('review'))
	
	data = session.get('checkbox_data', {}) 
	
	# Initialize checkbox data 

	preselected_special_notes = data.get('selected_special_notes', {}).get('preselected', []) or []  # Special Notes
	preselected_bw = data.get('selected_building_works', {}).get('preselected', []) or [] # Building Works
	preselected_pp = data.get('selected_pp', {}).get('preselected', []) or []  # Planning Permission
	preselected_ew = data.get('selected_ew', {}).get('preselected', []) or [] # External Wall
	preselected_fs = data.get('selected_fs', {}).get('preselected', []) or [] # Floor structure
	preselected_id = data.get('selected_id', {}).get('preselected', []) or [] # Internal doors
	preselected_dr = data.get('selected_dr', {}).get('preselected', []) or [] # Drainage
	preselected_wp = data.get('selected_wp', {}).get('preselected', []) or [] # Waste & Parking
	preselected_gv = data.get('selected_gv', {}).get('preselected', []) or [] # Glass Valley 
	preselected_bll = data.get('selected_bll', {}).get('preselected', []) or [] # Boundary Lines Left
	preselected_blr = data.get('selected_blr', {}).get('preselected', []) or [] # Boundary Lines Right
	preselected_rro = data.get('selected_rro', {}).get('preselected', []) or [] # Rear Reception Opening
	preselected_iw = data.get('selected_iw', {}).get('preselected', []) or []  # Internal Walls
	preselected_ab = data.get('selected_ab', {}).get('preselected', []) or []  # Additional Building Works
	preselected_el = data.get('selected_el', {}).get('preselected', []) or []  # Electrics
	preselected_pl = data.get('selected_pl', {}).get('preselected', []) or []  # Plumbing
	preselected_sk = data.get('selected_sk', {}).get('preselected', []) or []  # Skylights
	preselected_vl = data.get('selected_vl', {}).get('preselected', []) or []  # Velux Windows
	preselected_ac = data.get('selected_ac', {}).get('preselected', []) or []  # Aluminium Capping
	preselected_sld = data.get('selected_sld', {}).get('preselected', []) or []  # Sliding Doors
	preselected_oe = data.get('selected_oe', {}).get('preselected', []) or []  # Optional Extras
	preselected_fw = data.get('selected_fw', {}).get('preselected', []) or []  # Finishing Works
	
	# Initialize session data manual input

	client_address = session.get('data', {}).get('client_address', 'No address provided').strip()  # Project Address
	Date = session.get('data', {}).get('Date', 'No date provided').strip()  # Project Date
	lightwell_dimensions_input = session.get('data', {}).get('lightwell_dimensions_input', '').strip()  # Dimensions for courtyard lightwell (if applicable)
	other_council = session.get('data', {}).get('other_council', '').strip()  # Custom input if council is "Other"
	wall_height_metres = session.get('data', {}).get('wall_height_metres', '').strip()  # External wall height (Metres)
	wall_height_centimetres = session.get('data', {}).get('wall_height_centimetres', '').strip()  # External wall height (Centimetres)
	preselected_er = session.get('data', {}).get('selected_er', [])  # Selected roofing options
	pitched_roof_option = session.get('data', {}).get('pitched_roof_option', '')  # Specific pitched roof selection (if applicable)
	preselected_council = session.get('data', {}).get('selected_council', [])  # Selected council (from dropdown)
	other_roofing_description = session.get('data', {}).get('other_roofing_description', '').strip()  # Custom roofing description (if "Other" selected)
	fire_doors_number = session.get('data', {}).get('fire_doors_number', '').strip()  # Number of fire doors selected
	non_fire_doors_number = session.get('data', {}).get('non_fire_doors_number', '').strip()  # Number of non-fire doors selected
	drainage_other_input = session.get('data', {}).get('drainage_other_input', '').strip()  # Custom drainage input (if "Other" selected)
	other_demolition_option = session.get('data', {}).get('other_demolition_option', '').strip()  # Custom demolition input (if "Other" selected)
	sliding_door_area = session.get('data', {}).get('sliding_door_area', '').strip()  # Sliding door area input
	selected_kitchen_option = session.get('data', {}).get('selected_kitchen_option', '') # Selected Kitchen Option
	selected_loft_option = session.get('data', {}).get('selected_loft_option', '') # Selected Loft Option
	chimney_breast_option = session.get('data', {}).get('chimney_breast_option', '').strip() #CHimney Breast Option
	
	# Initalize float inputs

	other_demolition_cost = f"{float(session.get('data', {}).get('other_demolition_cost', 0)):.2f}"
	drainage_other_cost = f"{float(session.get('data', {}).get('drainage_other_cost', 0)):.2f}"
	iw_sqm_values = session.get('data', {}).get('iw_sqm_values', {})  # Default to empty dict
	iw_fixed_values = session.get('data', {}).get('iw_fixed_values', {})  # Default to empty dict
	kitchen_lights_amount = float(session.get('data', {}).get('elkl0_amount', 0))
	kitchen_points_amount = float(session.get('data', {}).get('elkp0_amount', 0))
	loft_lights_amount = float(session.get('data', {}).get('elll0_amount', 0))
	loft_points_amount = float(session.get('data', {}).get('ellp0_amount', 0))	
	
	# Initialize session data lists

	preselected_conservation_status = session.get('data', {}).get('conservation_status', [])
	preselected_basement = session.get('data', {}).get('selected_basement', [])
	preselected_dw = session.get('data', {}).get('selected_dw', []) or []
	
	# Fetch data from Google Sheets for descriptions

	fetched_data = fetch_data() or []
	line_code_descriptions = {row['Line Code']: row['Internal Description'] for row in fetched_data}
	
	if session.get('checkbox_data') and 'other_council' in session['checkbox_data'] and not other_council:
		session['checkbox_data'].pop('other_council')
		session.modified = True
		
	# Construct review_data dictionary

	review_data = {
			#Page 1			
			'Project Details': {
				'Client Address': client_address,
				'Date of Proposal': Date,
			},
			
			#Page 2
			'Special Notes': {
				'selected_special_notes': [
					line_code_descriptions.get(code, code)
					for code in data.get('selected_special_notes', {}).get('preselected', [])
				],
			},
			
			# Page 3
			'Summary': {
				#  Building & Demolition Works 
				'selected_building_works': [
					line_code_descriptions.get(code, code) for code in preselected_bw if code!= 'bw4^'
				] + (
					# Append lightwell details only if bw4^ is selected
					[f"{line_code_descriptions.get('bw4^', 'Courtyard Lightwell')} (dimensions = {lightwell_dimensions_input} meters squared)"]
					if 'bw4^' in preselected_bw and lightwell_dimensions_input else []
				),
				
				# Boundary Lines
				'selected_bll': [line_code_descriptions.get(code, code) for code in preselected_bll],
				'selected_blr': [line_code_descriptions.get(code, code) for code in preselected_blr],
				
				# Basement Section
				'selected_basement': [line_code_descriptions.get(code, code) for code in preselected_basement],
				
				# Planning Permission (Exclude ppx)
				'selected_pp': [line_code_descriptions.get(code, code) for code in preselected_pp if code != 'ppx'],
				
				# Conservation Area
				'conservation_status': [line_code_descriptions.get(code, code) for code in preselected_conservation_status],
								
				# Local Council
				'selected_council': [
					line_code_descriptions.get(code, code) for code in preselected_council if code != 'cs0'
				] + (
					[f"Other: {other_council}"] if 'cs0' in preselected_council and other_council else []
				),
			},
		
			# Page - Materials and Details 
			'Materials & Details': {
				# External Walls
				'selected_ew': [
					line_code_descriptions.get(code, code) for code in preselected_ew
				] + (
					[f"Wall Height (Metres): {wall_height_metres}"] if wall_height_metres else []
				) + (
					[f"Wall Height (Centimetres): {wall_height_centimetres}"] if wall_height_centimetres else []
				),
				
				# Roofing Option
				'selected_er': [
					line_code_descriptions.get(code, code) for code in preselected_er if code not in ['er1#']
				] + (
					[line_code_descriptions.get(code, code) for code in pitched_roof_option if code != 'er7^']
					if pitched_roof_option else []
				) + (
					[f"{line_code_descriptions.get('er7', 'Other Roofing')}: {other_roofing_description}"]
					if 'er7^' in pitched_roof_option and other_roofing_description else []
				),
			
				# Internal Doors
					'selected_id': [
						line_code_descriptions.get(code, code) for code in preselected_id  #  Converts line codes to descriptions
					] + (
						[f"Number of Fire Doors: {fire_doors_number}"] if fire_doors_number else []
					) + (
						[f"Number of Non-Fire Doors: {non_fire_doors_number}"] if non_fire_doors_number else []
					),
				
				# Drainage
					'selected_dr': [
						line_code_descriptions.get(code, code) for code in preselected_dr if code != 'dr4^'
					] + (
						[f"{line_code_descriptions.get('dr4^', 'Other Drainage Work')} {drainage_other_input}"]
						if 'dr4^' in preselected_dr and drainage_other_input else []
					) + (
						[f"Additional Drainage Cost: £{drainage_other_cost}"]
						if 'dr4^' in preselected_dr and drainage_other_cost else []
					),
				
				#  Waste & Parking
					'selected_wp': [
						line_code_descriptions.get(code, code) for code in preselected_wp
					],
				
				
			},
		
			# Page Further Requirements
			'Further Requirements': {
				
				# Demolition Works 
				'selected_dw': [
					line_code_descriptions.get(code, code) for code in preselected_dw if code not in ['dw0', 'dw4', 'dw6#']
				] + (
					[f"{line_code_descriptions.get('dw4#', 'Demolish Garden Wall')}"]
					if 'dw4' in preselected_dw else []
				) + (
					[f"Other Demolition Requirements: {other_demolition_option}"]
					if 'dw6#' in preselected_dw and other_demolition_option else []
				) + (
					[f"Additional Demolition Cost: £{other_demolition_cost}"]
					if 'dw6#' in preselected_dw and other_demolition_cost else []
				),
				
				# Floor Structure
				'selected_fs': [
					line_code_descriptions.get(code, code) for code in preselected_fs
				],
				
				# Galss Valley
				'selected_gv': [
					line_code_descriptions.get(code, code) for code in preselected_gv
				],
				
				# Roof Retention Options (🔹 NEW ADDITION)
				'selected_rro': [
						line_code_descriptions.get(code, code) for code in preselected_rro if code != 'rro0'
					],
				
				# Internal Walls (Only display SQM OR Fixed Cost, never both)
				'selected_iw': [
					f"{line_code_descriptions.get(code, code)}\n    * {session['data']['iw_sqm_values'].get(code, '')} sqm"
					if code in session['data'].get('iw_sqm_values', {})
					else f"{line_code_descriptions.get(code, code)}\n    * £{float(session['data']['iw_fixed_values'].get(code, 0)):.2f}"
					for code in data.get('selected_iw', {}).get('preselected', [])
				]
			},
			
			#Page Additional Buuilding Works
			'Additional Building Works': {
				'selected_ab': [
					line_code_descriptions.get(code, code)
					for code in data.get('selected_ab', {}).get('preselected', [])
				],
			},
			
			# Page - Additional Costs
			'Additional Costs': {
				
				# Electrics
					**(
						{"Kitchen Electrics": [
							line_code_descriptions.get(selected_kitchen_option, "Custom Option")
							if selected_kitchen_option != "elk0"
							else "Custom Configuration",
							{
								"  • Kitchen Lights": f"{kitchen_lights_amount} points"
								if kitchen_lights_amount else None,
								"  • Kitchen Power Points": f"{kitchen_points_amount} points"
								if kitchen_points_amount else None
							} if selected_kitchen_option == "elk0" else {}
						]} if 'elk1' in preselected_el else {}
					),
				
					**(
						{"Loft Electrics": [
							line_code_descriptions.get(selected_loft_option, "Custom Option")
							if selected_loft_option != "ell0"
							else "Custom Configuration",
							{
								"  • Loft Lights": f"{loft_lights_amount} points"
								if loft_lights_amount else None,
								"  • Loft Power Points": f"{loft_points_amount} points"
								if loft_points_amount else None
							} if selected_loft_option == "ell0" else {}
						]} if 'ell1' in preselected_el else {}
					),
				
					"Other Electrics": [
						line_code_descriptions.get(code, code)
						for code in preselected_el if code not in ("elk1", "ell1")
					],
				
				
					# **Plumbing**
					'selected_pl': [
						line_code_descriptions.get(code, code) for code in preselected_pl
					],
					
					# **Skylights**
					'selected_sk': [
						line_code_descriptions.get(code, code) for code in preselected_sk
					],
					
					# **Velux Windows**
					'selected_vl': [
						line_code_descriptions.get(code, code) for code in preselected_vl
					],
					
					# **Aluminium Capping**
					'selected_ac': [
						line_code_descriptions.get(code, code) for code in preselected_ac
					],
					
					# **Sliding Doors**
					'selected_sld': [
						line_code_descriptions.get(code, code) for code in preselected_sld
					] + (
						[f"Sliding Door Total Area: {sliding_door_area} sqm"]
						if sliding_door_area else []
					)
			},
		
			# Page - Optional Extras & Optional Finishing Works
			'Optional Extras & Finishing Works': {
				
				# Optional Extras
				'selected_oe': [
					line_code_descriptions.get(code, code)
					for code in preselected_oe
					if code not in ['oe1', 'oe111', 'oe112']
				] + (
					[f"Chimney Breast Type: {line_code_descriptions.get(chimney_breast_option, 'Not specified')}"]
					if 'oe1' in preselected_oe and chimney_breast_option in ['oe111', 'oe112']
					else []
				),
				
				# Finishing Works
				'selected_fw': [
					line_code_descriptions.get(code, code)
					for code in preselected_fw
				]
			},
	}
		
	# Map individual line codes to readable descriptions
	for key, value in review_data.items():
		if isinstance(value, list):  # For iterables like selected checkboxes
			review_data[key] = [TITLE_MAPPING.get(item, item) for item in value]
		elif isinstance(value, str):  # For single manual input values
			review_data[key] = TITLE_MAPPING.get(value, value)
	
	# Pass TITLE_MAPPING and other data to the template
	return render_template('review.html', review_page=True, review_data=review_data, TITLE_MAPPING=TITLE_MAPPING, current_page='review', title="Review Page")


#####################################################################################################################################

														# Submit route

#####################################################################################################################################

@app.route('/submit', methods=['POST'])
def submit():
	if request.method == 'POST':
		
		data = session.get('checkbox_data', {})
		sheet_data = fetch_data()
		combined_data = []
		
		if sheet_data:
			line_code_descriptions = {
				row['Line Code']: row['Internal Description'] for row in sheet_data
			}
		
		# Initialize checkbox data 
		preselected_special_notes = data.get('selected_special_notes', {}).get('preselected', []) or []
		preselected_bw = data.get('selected_building_works', {}).get('preselected', []) or []
		preselected_pp = data.get('selected_pp', {}).get('preselected', []) or []
		preselected_ew = data.get('selected_ew', {}).get('preselected', []) or []
		preselected_fs = data.get('selected_fs', {}).get('preselected', []) or []
		preselected_id = data.get('selected_id', {}).get('preselected', []) or []
		preselected_dr = data.get('selected_dr', {}).get('preselected', []) or []
		preselected_wp = data.get('selected_wp', {}).get('preselected', []) or []
		preselected_gv = data.get('selected_gv', {}).get('preselected', []) or []
		preselected_bll = data.get('selected_bll', {}).get('preselected', []) or []
		preselected_blr = data.get('selected_blr', {}).get('preselected', []) or []
		preselected_rro = data.get('selected_rro', {}).get('preselected', []) or []
		preselected_iw = data.get('selected_iw', {}).get('preselected', []) or []  
		preselected_ab = data.get('selected_ab', {}).get('preselected', []) or [] 
		preselected_el = data.get('selected_el', {}).get('preselected', []) or []  # Electrics
		preselected_pl = data.get('selected_pl', {}).get('preselected', []) or []  # Plumbing
		preselected_sk = data.get('selected_sk', {}).get('preselected', []) or []  # Skylights
		preselected_vl = data.get('selected_vl', {}).get('preselected', []) or []  # Velux Windows
		preselected_ac = data.get('selected_ac', {}).get('preselected', []) or []  # Aluminium Capping
		preselected_sld = data.get('selected_sld', {}).get('preselected', []) or []  # Sliding Doors
		preselected_oe = data.get('selected_oe', {}).get('preselected', []) or []  # Optional Extras
		preselected_fw = data.get('selected_fw', {}).get('preselected', []) or []  # Finishing Works
		
		# Initialize session data manual input
		client_address = session.get('data', {}).get('client_address', 'No address provided').strip()
		Date = session.get('data', {}).get('Date', 'No date provided').strip()
		lightwell_dimensions_input = session.get('data', {}).get('lightwell_dimensions_input', '').strip()
		other_council = session.get('data', {}).get('other_council', '').strip()
		wall_height_metres = session.get('data', {}).get('wall_height_metres', '').strip()
		wall_height_centimetres = session.get('data', {}).get('wall_height_centimetres', '').strip()
		pitched_roof_option = session.get('data', {}).get('pitched_roof_option', '')
		preselected_er = session.get('data', {}).get('selected_er', [])
		other_roofing_description= session.get('data', {}).get('other_roofing_description', '').strip()
		preselected_council = session.get('data', {}).get('selected_council', [])
		fire_doors_number = session.get('data', {}).get('fire_doors_number', '').strip()
		non_fire_doors_number = session.get('data', {}).get('non_fire_doors_number', '').strip()
		drainage_other_input = session.get('data', {}).get('drainage_other_input', '').strip()
		other_demolition_option = session.get('data', {}).get('other_demolition_option', '').strip()
		kitchen_power_points = session.get('data', {}).get('kitchen_power_points', '').strip()  # Kitchen power points
		kitchen_lighting_points = session.get('data', {}).get('kitchen_lighting_points', '').strip()  # Kitchen lighting points
		loft_power_points = session.get('data', {}).get('loft_power_points', '').strip()  # Loft power points
		loft_lighting_points = session.get('data', {}).get('loft_lighting_points', '').strip()  # Loft lighting points
		sliding_door_area = session.get('data', {}).get('sliding_door_area', '').strip()  # Sliding door area input
		selected_kitchen_option = session.get('data', {}).get('selected_kitchen_option', '') # Selected Kitchen Option
		selected_loft_option = session.get('data', {}).get('selected_loft_option', '') # Selected Loft Option
		
		# Initalize float inputs
		other_demolition_cost = f"{float(session.get('data', {}).get('other_demolition_cost', 0)):.2f}"
		drainage_other_cost = f"{float(session.get('data', {}).get('drainage_other_cost', 0)):.2f}"
		kitchen_lights_amount = float(session.get('data', {}).get('elkl0_amount', 0))
		kitchen_points_amount = float(session.get('data', {}).get('elkp0_amount', 0))
		loft_lights_amount = float(session.get('data', {}).get('elll0_amount', 0))
		loft_points_amount = float(session.get('data', {}).get('ellp0_amount', 0))	
		
		#Initialise multiple dictionary floats (e.g. iw) to 
		iw_sqm_values = {
			key: f"{to_float(value):.2f}" for key, value in session.get('data', {}).get('iw_sqm_values', {}).items() if value
		}
		
		iw_fixed_values = {
			key: f"{to_float(value):.2f}" for key, value in session.get('data', {}).get('iw_fixed_values', {}).items() if value
		}
	
		# Initialize session data lists
		preselected_conservation_status = session.get('data', {}).get('conservation_status', [])
		preselected_basement = session.get('data', {}).get('selected_basement', [])
		preselected_dw = session.get('data', {}).get('selected_dw', []) or []
			
		# Append session and checkbox_data  to combined data
		combined_data += (
			(preselected_special_notes or []) + 
			(preselected_bw or []) + 
			(preselected_dw or []) + 
			(preselected_pp or []) + 
			(preselected_council or []) + 
			(preselected_conservation_status or []) + 
			(preselected_bll or []) + 
			(preselected_blr or []) + 
			(preselected_basement or []) +
			(preselected_er or []) +
			(pitched_roof_option or [])+
			(preselected_ew or []) +
			(preselected_fs or []) +
			(preselected_id or []) +
			(preselected_dr or []) +
			(preselected_wp or []) +
			(preselected_gv or []) +
			(preselected_rro or []) +
			(preselected_iw or []) +
			(preselected_ab or []) +
			(preselected_el or []) +
			(preselected_pl or []) +
			(preselected_sk or []) +
			(preselected_vl or []) +
			(preselected_ac or []) +
			(preselected_sld or []) +
			(preselected_oe or []) +
			(preselected_fw or [])
		)
				
		# initalize descriptions to update
		submit_to_description_function = {}
		
		# Project details
		if client_address:
			submit_to_description_function['client_address'] = client_address
		
		if Date:
			submit_to_description_function['Date'] = Date
			
		# Lightwell Additional Input 
		if lightwell_dimensions_input:
			submit_to_description_function['lightwell_dimensions_input'] = lightwell_dimensions_input 
			
		# Council Section 'Other' input
		if 'cs0' in preselected_council and other_council:
			submit_to_description_function['other_council'] = other_council
		
		# Roofing Options 'Other' input
		if other_roofing_description:
			submit_to_description_function['other_roofing_description'] = other_roofing_description
			
		# Wall Height
		if wall_height_metres:
			submit_to_description_function['wall_height_metres'] = wall_height_metres
			
		if wall_height_centimetres:
			submit_to_description_function['wall_height_centimetres'] = wall_height_centimetres
			
		# Internal Doors
		if non_fire_doors_number:
			submit_to_description_function['non_fire_doors_number'] = non_fire_doors_number
			
		if fire_doors_number:
			submit_to_description_function['fire_doors_number'] = fire_doors_number

		# Drainage_other
		if drainage_other_input:
			submit_to_description_function['drainage_other_input'] = drainage_other_input 
		
		if drainage_other_cost:
			submit_to_description_function['drainage_other_cost'] = drainage_other_cost
				
		# Demolition Other Amount and cost
		if 	other_demolition_option:
			submit_to_description_function['other_demolition_option'] = other_demolition_option
		
		if 	other_demolition_cost:
			submit_to_description_function['other_demolition_cost'] = other_demolition_cost
		
		if iw_sqm_values:
			submit_to_description_function['iw_sqm_values'] = iw_sqm_values
		
		if iw_fixed_values:
			submit_to_description_function['iw_fixed_values'] = iw_fixed_values

		if kitchen_power_points:
			submit_to_description_function['kitchen_power_points'] = kitchen_power_points
			
		if kitchen_lighting_points:
			submit_to_description_function['kitchen_lighting_points'] = kitchen_lighting_points
			
		if loft_power_points:
			submit_to_description_function['loft_power_points'] = loft_power_points
			
		if loft_lighting_points:
			submit_to_description_function['loft_lighting_points'] = loft_lighting_points
			
		if sliding_door_area:
			submit_to_description_function['sliding_door_area'] = sliding_door_area
		
		print("Debug - Submitting to update_description_column:", submit_to_description_function)
		
		if submit_to_description_function:  
			description_column_includes = update_description_column(**submit_to_description_function) or []
		
		# Debug log before updating "Include" column
		print(f"DEBUG: Combined Data for Include Column: {combined_data}")
		
		# Pass BOTH checkbox selections & updated descriptions to update_include_column()
		update_include_column(combined_data, description_column_includes)
	
		return jsonify({'status': 'success', 'message': 'Data successfully updated!'})
	

#####################################################################################################################################

							# Route for the production page (trigger production script)
	
#####################################################################################################################################
	
@app.route('/production-page')
def trigger_production_page():
	return render_template('production.html')


#####################################################################################################################################

								# Trigger production script when button clicked

#####################################################################################################################################

@app.route('/trigger_production')
def trigger_production():
	try:
		if TEST_MODE:
			return """
			<h2>Your document is ready!</h2>
			<p>
				<a href="https://example.com/test-document" target="_blank" class="btn">Click here to open it in a new tab</a>
			</p>
			"""

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

#####################################################################################################################################
	
if __name__ == '__main__': 
	debug_mode = os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes', 'on'}
	port = int(os.getenv('PORT', '5000'))
	app.run(debug=debug_mode, port=port)
	
#####################################################################################################################################
	
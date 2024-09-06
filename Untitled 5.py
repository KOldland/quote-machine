#!/usr/bin/env python3

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
	# Generate combined total for combined_total
	combined_prefixes = ['bw', 'dw', 'ew', 'er', 'fs', 'ps']
	combined_total = sum(totals[prefix] for prefix in combined_prefixes)
	doc_requests.append({'replaceAllText': {'containsText': {'text': '<combined_total>', 'matchCase': True}, 'replaceText': f"£{combined_total:.2f}"}})
	print(f"Replaced <combined_total> with £{combined_total:.2f}")
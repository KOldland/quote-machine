console.log('JS file loaded and running!');
const isBuilderBetaPage = window.location.pathname.startsWith('/builder_beta/');

// --------------------- 1️⃣ ACCORDION & SIDEBAR ---------------------

function toggleAccordion(sectionId) {
	const section = document.getElementById(sectionId);
	if (section.style.display === "none" || section.style.display === "") {
		section.style.display = "block";
	} else {
		section.style.display = "none";
	}
}

document.getElementById('sidebarToggle')?.addEventListener('click', function () {
	const sidebar = document.getElementById('sidebar');
	const mainContent = document.querySelector('.main-content');
	sidebar.classList.toggle('collapsed');
	mainContent.classList.toggle('expanded');
});

// --------------------- 2️⃣ CHECKBOX & DROPDOWN VISIBILITY ---------------------

function toggleVisibility(checkboxId, dropdownId, resetElementId = null) {
	console.log(`toggleVisibility Called - Checkbox: ${checkboxId}, Dropdown: ${dropdownId}`);
	
	const checkbox = document.getElementById(checkboxId);
	const dropdown = document.getElementById(dropdownId);
	
	if (checkbox && dropdown) {
		console.log(" Checkbox and Dropdown Found!");
		
		if (checkbox.type === "checkbox") {
			// Standard checkbox toggling
			dropdown.style.display = checkbox.checked ? "block" : "none";
		} else if (checkbox.tagName === "SELECT") {
			// Dropdown toggling based on a specific match value
			dropdown.style.display = checkbox.value === resetElementId ? "block" : "none";
		}
	} else {
		console.warn(`toggleVisibility - Missing elements: Checkbox (${checkbox}), Dropdown (${dropdown})`);
	}
}

// --------------------- 3️⃣ "OTHER" TEXT INPUT TOGGLE ---------------------

function toggleOtherInput(dropdownId, inputContainerId, inputFieldId, matchValue) {
	const dropdown = document.getElementById(dropdownId);
	const inputContainer = document.getElementById(inputContainerId);
	const inputField = document.getElementById(inputFieldId);
	
	if (dropdown && inputContainer) {
		if (dropdown.value === matchValue) {
			inputContainer.style.display = 'block';
		} else {
			inputContainer.style.display = 'none';
			if (inputField) inputField.value = ''; // Clear input when hidden
		}
	}
}

// --------------------- 4️⃣ INTERNAL WALL HANDLING ---------------------

function toggleIWInputs(lineCode) {
	const dropdown = document.querySelector(`#iwType_${CSS.escape(lineCode)}`);
	const sqmInput = document.querySelector(`#iwSqmInput_${CSS.escape(lineCode)}`);
	const fixedInput = document.querySelector(`#iwFixedInput_${CSS.escape(lineCode)}`);
	
	if (dropdown) {
		sqmInput.style.display = dropdown.value === "sqm" ? "block" : "none";
		fixedInput.style.display = dropdown.value === "fixed" ? "block" : "none";
	}
}

// --------------------- 5️⃣ MUTUAL EXCLUSIVITY HANDLING ---------------------

function enforceMutualExclusivity(yesCheckboxId, noCheckboxId) {
	const yesCheckbox = document.getElementById(yesCheckboxId);
	const noCheckbox = document.getElementById(noCheckboxId);
	
	if (yesCheckbox && noCheckbox) {
		yesCheckbox.addEventListener('change', () => { if (yesCheckbox.checked) noCheckbox.checked = false; });
			noCheckbox.addEventListener('change', () => { if (noCheckbox.checked) yesCheckbox.checked = false; });
	} else {
			console.error(`Error: Could not find ${yesCheckboxId} or ${noCheckboxId}`);
	}
}

// --------------------- 6️⃣ FLOOR STRUCTURE & DEMOLITION HANDLING ---------------------
				
function toggleFloorStructure() {
	let dwCheckBoxes = ['dw7', 'dw8', 'dw9', 'dw10'].map(id => document.querySelector(`input[value="${id}"]`));
	let fs3 = document.querySelector('input[value="fs3#"]');
	let fs4 = document.querySelector('input[value="fs4#"]');
	
	if (event) {
		let selected = event.target;
		if (selected.checked) {
			dwCheckBoxes.forEach(dw => { if (dw !== selected) dw.checked = false; });
		}
	}
				
	let selectedDWs = dwCheckBoxes.some(dw => dw?.checked);
	fs3.checked = selectedDWs;
	fs4.checked = dwCheckBoxes[0]?.checked;
	
	if (!selectedDWs) {
		fs3.checked = false;
		fs4.checked = false;
	}
}

// --------------------- 6.5 Demolition Works Input ---------------------
				
function updateDemolitionInputs() {
	const demolitionDropdown = document.getElementById('selected_dw');
	const demolitionCheckbox = document.getElementById('demolitionCheckbox');
	const otherInputs = document.getElementById('otherDemolitionInputs');
	
	if (!otherInputs) return;
	
	// If either element is missing, fallback to hiding
	if (!demolitionDropdown || !demolitionCheckbox) {
		otherInputs.style.display = 'none';
		return;
	}
	
	const dropdownIsOther = demolitionDropdown.value === "dw6#";
	const checkboxIsChecked = demolitionCheckbox.checked;
	
	if (dropdownIsOther && checkboxIsChecked) {
		otherInputs.style.display = 'block';
	} else {
		otherInputs.style.display = 'none';
	}
}

		
// --------------------- 7️⃣ GLASS VALLEY LOGIC ---------------------
				
function toggleGlassValley() {
	let gv1 = document.querySelector('input[value="gv1"]');
	let gv2 = document.querySelector('input[value="gv2"]');
	let gv3 = document.querySelector('input[value="gv3#"]'); 
	let gv3Children = document.querySelectorAll('input[name="selected_gv"][value^="gv3"]:not([value="gv3#"])');
	
	gv3.checked = gv1.checked || gv2.checked;
	gv3Children.forEach(child => { child.checked = gv3.checked; });
}

// --------------------- 8️⃣ ELECTRICS SECTION (KITCHEN & LOFT) ---------------------
				
function toggleManualInputs(dropdownId, inputSelectors, matchValue) {
	const dropdown = document.getElementById(dropdownId);
	const inputs = document.querySelectorAll(inputSelectors);
	
	if (dropdown) {
		const show = dropdown.value === matchValue;
		inputs.forEach(input => {
			input.style.display = show ? 'block' : 'none';
			if (!show) input.querySelector('input').value = '';
		});
	}
}

// ---------------------  Step 5.5 Mutual exclusivity ---------------------
function updateDrainageInputs() {
	const drainageCheckbox = document.querySelector('input[name="selected_dr"][value="dr4^"]');
	const otherInputContainer = document.getElementById('drainageOtherInputContainer');
	const costField = document.getElementById('drainage_other_cost');
	
	if (drainageCheckbox && otherInputContainer && costField) {
		if (drainageCheckbox.checked) {
			otherInputContainer.style.display = 'block';
			costField.style.display = 'inline-block';
		} else {
			otherInputContainer.style.display = 'none';
			costField.style.display = 'none';
			costField.value = '';
		}
	}
				}
// --------------------- 9️⃣ INITIALIZATION ON PAGE LOAD ---------------------

	document.addEventListener('DOMContentLoaded', function () {
		if (isBuilderBetaPage) {
			console.log('Builder beta route detected, skipping legacy form page initializers.');
			return;
		}
		console.log(' DOM fully loaded, initializing functionality...');
		
		// Step 1: Toggle visibility pairs
		console.log('Step 1: Toggle visibility pairs...');
		[
			['demolitionCheckbox', 'demolitionSizeDropdown'],
			['bllCheckbox', 'boundarySizeDropdownLeft'],
			['blrCheckbox', 'boundarySizeDropdownRight'],
			['ppCheckbox', 'planningPermissionDropdown'],
			['pitchedRoofCheckbox', 'pitchedRoofDropdown'],
			['wallHeightCheckbox', 'wallHeightInput'],
			['courtyardLightwellCheckbox', 'lightwellInputContainer'],
			['drainageOtherCheckbox', 'drainageOtherInputContainer'],
			['receptionOpeningCheckbox', 'receptionOpeningDropdown'],
			['chimneyBreastCheckbox','chimneyDropdown']
		].forEach(([checkboxId, dropdownId]) => {
			const checkbox = document.getElementById(checkboxId);
			const dropdown = document.getElementById(dropdownId);
			
			if (checkbox && dropdown) {
				console.log(`Found: ${checkboxId} + ${dropdownId}`);
				toggleVisibility(checkboxId, dropdownId);
			} else {
				console.log(`Skipping ${checkboxId} - Not found on this page.`);
			}
		});
		
		// Step 2: Internal wall dropdown logic
		console.log('Step 2: IW dropdown event listeners...');
		document.querySelectorAll('input[name="selected_iw"]').forEach(checkbox => {
			let lineCode = checkbox.value;
			let dropdownId = `iwDropdown_${lineCode}`;
			checkbox.addEventListener('change', () => toggleVisibility(lineCode, dropdownId));
		});
		
		// Step 2.5: Roofing Dropdown Toggle
		console.log('Step X: Roofing dropdown toggle listener...');
		const pitchedCheckbox = document.getElementById('pitchedRoofCheckbox');
		if (pitchedCheckbox) {
			pitchedCheckbox.addEventListener('change', () => {
				toggleVisibility('pitchedRoofCheckbox', 'pitchedRoofDropdown');
			});
		}
		
		// Step 2.6: Initialize IW input visibility based on dropdown selection
		console.log('Step 2.6: Preload IW input visibility...');
		document.querySelectorAll('input[name="selected_iw"]').forEach(checkbox => {
			const lineCode = checkbox.value;
			const dropdown = document.getElementById(`iwType_${lineCode}`);
			if (dropdown) toggleIWInputs(lineCode);
		});
		
		// Step 2.7: Kitchen & Loft checkbox → config toggle
		console.log('Step 2.7: Kitchen/Loft checkbox toggles...');
		const kitchenCheckbox = document.querySelector('input[name="selected_kitchen_el"][value="elk1"]');
		const kitchenOptions = document.getElementById('kitchenElectricsOptions');
		
		if (kitchenCheckbox && kitchenOptions) {
			kitchenCheckbox.addEventListener('change', () => {
				kitchenOptions.style.display = kitchenCheckbox.checked ? 'block' : 'none';
			});
			kitchenOptions.style.display = kitchenCheckbox.checked ? 'block' : 'none';
		}
		
		const loftCheckbox = document.querySelector('input[name="selected_loft_el"][value="ell1"]');
		const loftOptions = document.getElementById('loftElectricsOptions');
		
		if (loftCheckbox && loftOptions) {
			loftCheckbox.addEventListener('change', () => {
				loftOptions.style.display = loftCheckbox.checked ? 'block' : 'none';
			});
			loftOptions.style.display = loftCheckbox.checked ? 'block' : 'none';
		}
		
		// Step 2.9: Skylight checkbox (sk0) → toggle dropdown and extras
		console.log('Step 2.9: Skylight checkbox toggle...');
		const skylightCheckbox = document.querySelector('input[name="selected_sk"][value="sk0"]');
		const skylightDropdown = document.getElementById('skylightDropdown');
		const skylightExtraOptions = document.getElementById('skylightExtraOptions');
		
		if (skylightCheckbox) {
			const toggleSkylights = () => {
				const show = skylightCheckbox.checked;
				if (skylightDropdown) skylightDropdown.style.display = show ? 'block' : 'none';
				if (skylightExtraOptions) skylightExtraOptions.style.display = show ? 'block' : 'none';
			};
			
			skylightCheckbox.addEventListener('change', toggleSkylights);
			toggleSkylights(); // Run once on load
		}


		// Step 3: "Other" text inputs
		console.log('Step 3: Other text inputs...');
		toggleOtherInput('pitchedRoofOptions', 'otherRoofingInput', 'otherRoofingText', 'er7^');
		toggleOtherInput('selected_council', 'otherCouncilInput', 'other_council', 'cs0');
		
		// Step 4: Demolition listeners
		console.log('Step 4: Demolition dropdown logic...');
		document.getElementById('selected_dw')?.addEventListener('change', updateDemolitionInputs);
		document.getElementById('demolitionCheckbox')?.addEventListener('change', updateDemolitionInputs);
		
		document.querySelectorAll('input[name="selected_dw"]').forEach(checkbox => {
			checkbox.addEventListener('change', toggleFloorStructure);
		});
		
		updateDemolitionInputs();  //  One-time call on page load

		
		// Step 5: Glass Valley logic
		console.log('Step 5: Glass Valley setup...');
		document.querySelectorAll('input[name="selected_gv"]').forEach(checkbox =>
			checkbox.addEventListener('change', toggleGlassValley)
		);
		try {
			toggleGlassValley();
		} catch (e) {
			console.warn(' toggleGlassValley failed:', e.message);
		}
		
		// Step 5.5: Drainage "Other" toggle
		console.log('Step 5.5: Drainage "Other" toggle...');
		document.querySelector('input[name="selected_dr"][value="dr4^"]')?.addEventListener('change', updateDrainageInputs);
		updateDrainageInputs();  // Trigger immediately on load
		
		// Step 6: Mutual exclusivity
		console.log('Step 6: Mutual exclusivity setup...');
		const cs8 = document.getElementById('cs8Checkbox');
		const cs9 = document.getElementById('cs9Checkbox');
		const bs1 = document.getElementById('bs1Checkbox');
		const bs2 = document.getElementById('bs2Checkbox');
		
		if (cs8 && cs9) {
			console.log(' Enforcing: cs8 <-> cs9');
			enforceMutualExclusivity('cs8Checkbox', 'cs9Checkbox');
		} else {
			console.log(" Skipping cs8/cs9 - Not found on this page.");
		}
		
		if (bs1 && bs2) {
			console.log('Enforcing: bs1 <-> bs2');
			enforceMutualExclusivity('bs1Checkbox', 'bs2Checkbox');
		} else {
			console.log("Skipping bs1/bs2 - Not found on this page.");
		}
		
		//  Step 7: Kitchen + Loft toggles
		console.log('Step 7: Electrics manual input toggles...');
		document.getElementById('selected_kitchen_option')?.addEventListener('change', () => {
			toggleManualInputs('selected_kitchen_option', '#kitchen_lights_input, #kitchen_points_input', 'elk0');
		});
		toggleManualInputs('selected_kitchen_option', '#kitchen_lights_input, #kitchen_points_input', 'elk0');
		
		document.getElementById('selected_loft_option')?.addEventListener('change', () => {
			toggleManualInputs('selected_loft_option', '#loft_lights_input, #loft_points_input', 'ell0');
		});
		toggleManualInputs('selected_loft_option', '#loft_lights_input, #loft_points_input', 'ell0');
		
		// Step X: Open accordion from server state (if any)
		const initiallyOpen = document.querySelector('.accordion-body.active');
		if (initiallyOpen) {
			initiallyOpen.style.display = 'block';
		}

		console.log('Initialization complete!');
		
		// Step 8: Finishing Works dropdown toggles
		console.log('Step 8: Finishing Works toggles...');
		
		[
			{ checkboxId: 'fw1_toggle', dropdownId: 'fw1_dropdown' },
			{ checkboxId: 'fw3_toggle', dropdownId: 'fw3_dropdown' },
			{ checkboxId: 'fw4_toggle', dropdownId: 'fw4_dropdown' },
			{ checkboxId: 'fw5_toggle', dropdownId: 'fw5_dropdown' },
			{ checkboxId: 'fw6_toggle', dropdownId: 'fw6_dropdown' },
		].forEach(({ checkboxId, dropdownId }) => {
			const checkbox = document.getElementById(checkboxId);
			const dropdown = document.getElementById(dropdownId);
			
			if (checkbox && dropdown) {
				console.log(`Setting toggle for ${checkboxId} → ${dropdownId}`);
				checkbox.addEventListener('change', () => {
					dropdown.style.display = checkbox.checked ? 'block' : 'none';
				});
				// Run once on load
				dropdown.style.display = checkbox.checked ? 'block' : 'none';
			} else {
				console.warn(`Toggle setup failed for ${checkboxId} or ${dropdownId}`);
			}
		}); 
	});
				
// --------------------- 10 IMAGE SELECTION TOGGLE ---------------------

	if (!isBuilderBetaPage) {
		document.querySelectorAll('.image-thumb.selectable').forEach(thumb => {
			thumb.addEventListener('click', function () {
				const checkbox = this.querySelector('input[type="checkbox"]');
				if (checkbox) {
					checkbox.checked = !checkbox.checked;
					this.classList.toggle('selected', checkbox.checked);
				}
			});
		});
	}
				

// --------------------- 11️⃣ LAYOUT TEMPLATE SELECTION ---------------------

document.addEventListener('DOMContentLoaded', function () {
	const previews = document.querySelectorAll('.template-preview');
	const layoutForm = document.querySelector('form[action*="image_upload_page"]');
	
	if (!layoutForm) return;
	
	let hiddenInput = layoutForm.querySelector('input[name="selected_template"]');
	if (!hiddenInput) {
		hiddenInput = document.createElement('input');
		hiddenInput.type = 'hidden';
		hiddenInput.name = 'selected_template';
		layoutForm.appendChild(hiddenInput);
	}
	
	previews.forEach(preview => {
		preview.addEventListener('click', function () {
			previews.forEach(p => p.classList.remove('selected-template'));
			this.classList.add('selected-template');
			const key = this.querySelector('p')?.innerText.trim();
			hiddenInput.value = key;
		});
	});
});

function loadNextRow() {
	const section = document.getElementById('more-templates');
	if (section) section.classList.remove('d-none');
}

function loadAllRows() {
	const section = document.getElementById('more-templates');
	if (section) section.classList.remove('d-none');
}


				
// Optional Fallback (only triggers if DOMContentLoaded didn't fire)
window.onload = () => {
	if (!isBuilderBetaPage) {
		console.log(" Window onload fallback triggered.");
	}
};
				
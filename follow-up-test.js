// Test the follow-up selector logic in browser console.
// Paste this into the browser Developer Tools console while on the form preview page.

// Test 1: Check if any follow-up checkboxes exist
console.log("=== Test 1: Find all follow-up checkboxes ===");
var followUpCheckboxes = document.querySelectorAll('.preview-checkbox-input[data-follow-up="1"]');
console.log("Found", followUpCheckboxes.length, "checkboxes with data-follow-up=\"1\"");

// Test 2: Check if any follow-up containers exist  
console.log("\n=== Test 2: Find all follow-up containers ===");
var followUpContainers = document.querySelectorAll('.preview-follow-up');
console.log("Found", followUpContainers.length, "follow-up containers");

// Test 3: Show details about the first follow-up checkbox
if (followUpCheckboxes.length > 0) {
    console.log("\n=== Test 3: Details about first checkbox ===");
    var checkbox = followUpCheckboxes[0];
    console.log("Checkbox value:", checkbox.value);
    console.log("Checkbox checked:", checkbox.checked);
    console.log("Checkbox has data-follow-up attr:", checkbox.getAttribute('data-follow-up'));
    console.log("Checkbox class:", checkbox.className);
    
    // Find matching container
    var matchValue = checkbox.value;
    var container = document.querySelector('.preview-follow-up[data-follow-up-for="' + matchValue + '"]');
    console.log("Matching container found:", container !== null);
    if (container) {
        console.log("Container display style:", container.style.display);
        console.log("Container content:", container.innerHTML.substring(0, 200));
    }
}

// Test 4: Add event listener to first checkbox
if (followUpCheckboxes.length > 0) {
    console.log("\n=== Test 4: Adding event listener test ===");
    var checkbox = followUpCheckboxes[0];
    checkbox.addEventListener('change', function() {
        console.log("Checkbox changed! New value:", this.checked);
        // Find matching container
        var container = document.querySelector('.preview-follow-up[data-follow-up-for="' + this.value + '"]');
        if (container) {
            console.log("Toggle container display to:", this.checked ? 'block' : 'none');
            container.style.display = this.checked ? 'block' : 'none';
        }
    });
    console.log("Event listener added to first checkbox");
}

// Test 5: Manually trigger the follow-up container display
if (followUpCheckboxes.length > 0) {
    console.log("\n=== Test 5: Manually trigger display ===");
    var checkbox = follow-upCheckboxes[0];
    checkbox.checked = true;
    // Manually trigger the change event
    checkbox.dispatchEvent(new Event('change'));
}

console.log("\n=== All tests complete ===");
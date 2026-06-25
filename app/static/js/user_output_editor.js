// ===== Global State =====
let currentTemplate = null;
let selectedSection = null;
let formKey = null;

// ===== Initialize on Page Load =====
document.addEventListener('DOMContentLoaded', function() {
    // Get form_key from URL parameter or default
    const urlParams = new URLSearchParams(window.location.search);
    formKey = urlParams.get('form_key') || 'default';
    
    // Update page title
    document.querySelector('.editor-toolbar h1').textContent = `Output Template Editor - ${formKey}`;
    
    // Load the output template
    loadTemplate();
    
    // Set up event listeners
    setupEventListeners();
});

// ===== Event Listeners Setup =====
function setupEventListeners() {
    // Sidebar section clicks
    document.querySelectorAll('.section-card').forEach(card => {
        card.addEventListener('click', function() {
            const section = this.dataset.section;
            selectSection(section);
        });
    });
    
    // Save button
    document.getElementById('save-btn').addEventListener('click', function() {
        saveTemplate();
    });
    
    // Reset button
    document.getElementById('reset-btn').addEventListener('click', function() {
        resetTemplate();
    });
    
    // Refresh preview button
    document.getElementById('refresh-preview-btn').addEventListener('click', function() {
        renderPreview();
    });
}

// ===== API Functions =====

/**
 * GET /api/output_template/<form_key>
 * Loads the current output template from the backend
 */
async function loadTemplate() {
    try {
        const response = await fetch(`/api/output_template/${formKey}`);
        if (!response.ok) throw new Error('Failed to load template');
        
        const data = await response.json();
        currentTemplate = data.template;
        renderPreview();
        selectSection('header');  // Default to header section
        
        console.log('Template loaded:', currentTemplate);
    } catch (error) {
        console.error('Error loading template:', error);
        showNotification('Failed to load template. Please try again.', 'error');
    }
}

/**
 * POST /api/output_template/<form_key>
 * Saves the updated template to the backend
 */
async function saveTemplate() {
    try {
        const response = await fetch(`/api/output_template/${formKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sections: currentTemplate.sections,
                css: currentTemplate.css
            })
        });
        
        if (!response.ok) throw new Error('Failed to save');
        
        showNotification('Template saved successfully!', 'success');
        renderPreview();  // Refresh preview after save
    } catch (error) {
        console.error('Error saving template:', error);
        showNotification('Failed to save template', 'error');
    }
}

/**
 * POST /api/output_template/<form_key>/reset
 * Resets template to default
 */
async function resetTemplate() {
    if (!confirm('Are you sure you want to reset to default template?')) return;
    
    try {
        const response = await fetch(`/api/output_template/${formKey}/reset`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to reset');
        
        const data = await response.json();
        currentTemplate = data.template || currentTemplate;
        renderPreview();
        selectSection(selectedSection);  // Refresh properties panel
        showNotification('Template reset to default', 'success');
    } catch (error) {
        console.error('Error resetting template:', error);
        showNotification('Failed to reset template', 'error');
    }
}

/**
 * GET /api/output_template/<form_key>/preview
 * Fetches rendered HTML for live preview
 */
async function renderPreview() {
    try {
        const response = await fetch(`/api/output_template/${formKey}/preview`);
        if (!response.ok) throw new Error('Failed to load preview');
        
        const html = await response.text();
        const previewFrame = document.getElementById('preview-frame');
        const frameDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
        
        frameDoc.open();
        frameDoc.write(html);
        frameDoc.close();
    } catch (error) {
        console.error('Error rendering preview:', error);
    }
}

// ===== UI Interaction Functions =====

/**
 * Handles section selection in sidebar
 */
function selectSection(sectionName) {
    selectedSection = sectionName;
    
    // Update sidebar active state
    document.querySelectorAll('.section-card').forEach(card => {
        card.classList.remove('active');
        if (card.dataset.section === sectionName) {
            card.classList.add('active');
        }
    });
    
    // Render properties panel
    renderPropertiesPanel(sectionName);
}

/**
 * Renders the properties panel based on selected section
 */
function renderPropertiesPanel(sectionName) {
    const container = document.getElementById('properties-content');
    const sectionData = currentTemplate.sections[sectionName];
    
    if (!sectionData) {
        container.innerHTML = '<p class="placeholder-text">Section not found</p>';
        return;
    }
    
    let html = '';
    
    if (sectionName === 'header') {
        html = renderHeaderProperties(sectionData);
    } else if (sectionName === 'body') {
        html = renderBodyProperties(sectionData);
    } else if (sectionName === 'footer') {
        html = renderFooterProperties(sectionData);
    } else if (sectionName === 'styling') {
        html = renderStylingProperties();
    }
    
    container.innerHTML = html;
    
    // Attach change listeners to inputs
    attachPropertyChangeListeners();
}

/**
 * Renders Header section properties
 */
function renderHeaderProperties(data) {
    return `
        <div class="section-header">Header Properties</div>
        
        <div class="property-group">
            <label>Enabled</label>
            <label class="checkbox-label">
                <input type="checkbox" data-field="enabled" ${data.enabled ? 'checked' : ''}>
                Show header on output
            </label>
        </div>
        
        <div class="property-group">
            <label>Show Logo</label>
            <label class="checkbox-label">
                <input type="checkbox" data-field="show_logo" ${data.show_logo ? 'checked' : ''}>
                Display company logo
            </label>
        </div>
        
        <div class="property-group">
            <label>Logo URL</label>
            <input type="url" data-field="logo_url" value="${data.logo_url || ''}" placeholder="/static/images/logo.png">
        </div>
        
        <div class
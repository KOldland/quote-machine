document.addEventListener('DOMContentLoaded', () => {
    const isEditMode = document.body.classList.contains('builder-edit-mode');

    if (!isEditMode) return;

    // State (from Flask-injected global variables)
    let selectedBlockId = typeof window.selectedBlockId !== 'undefined' ? window.selectedBlockId : null;
    let blocks = typeof window.blocks !== 'undefined' ? window.blocks : [];
    let pageId = typeof window.pageId !== 'undefined' ? window.pageId : '';
    let builderStateQuestionTypes = typeof window.builderStateQuestionTypes !== 'undefined' ? window.builderStateQuestionTypes : {};

    // History for Undo/Redo
    let history = [JSON.stringify(blocks)];
    let historyIndex = 0;

    // DOM Elements
    const canvasContent = document.getElementById('canvas-content');
    const propertiesContent = document.getElementById('properties-content');
    const saveStatus = document.getElementById('save-status');
    const pageSelect = document.getElementById('page-select');
    const btnAddBlock = document.getElementById('btn-add-block');
    const btnSave = document.getElementById('btn-save');
    const btnUndo = document.getElementById('btn-undo');
    const btnRedo = document.getElementById('btn-redo');
    const btnPreviewFloat = document.getElementById('preview-btn-float');
    const editActionStatus = document.getElementById('edit-action-status');

    // Init Callbacks
    setupDragAndDrop();
    setupEventListeners();
    renderCanvas();
    if (selectedBlockId) {
        selectBlock(selectedBlockId);
    } else {
        renderProperties();
    }
    updateUndoRedoButtons();

    // Utility to update edit mode status messages
    function setEditStatus(message, color) {
        if (editActionStatus) {
            editActionStatus.textContent = message;
            editActionStatus.style.color = color || '#6c757d';
        }
    }

    // Drag and Drop Logic
    function setupDragAndDrop() {
        const typeItems = document.querySelectorAll('.question-type-item');
        const canvas = document.getElementById('canvas-content');
        let draggedBlock = null; // For reordering existing blocks

        // Draggable Question Types from Palette
        typeItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('application/json', JSON.stringify({
                    type: item.dataset.type,
                    template: getBlockTemplate(item.dataset.type)
                }));
                item.classList.add('dragging');
            });
            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });
        });

        // Dragging existing blocks on canvas
        canvas.addEventListener('dragstart', (e) => {
            const blockEl = e.target.closest('.question-block');
            if (blockEl) {
                draggedBlock = blockEl;
                e.dataTransfer.setData('text/plain', blockEl.dataset.blockId);
                e.dataTransfer.effectAllowed = 'move';
                blockEl.classList.add('dragging');
            }
        });

        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            if (e.target.closest('.question-block') || e.target.id === 'canvas-content') {
                e.dataTransfer.dropEffect = 'move';
                // Add visual feedback for reordering
                const targetBlock = e.target.closest('.question-block');
                if (targetBlock && draggedBlock && targetBlock !== draggedBlock) {
                    const bounding = targetBlock.getBoundingClientRect();
                    const offset = e.clientY - bounding.top;
                    if (offset < bounding.height / 2) {
                        targetBlock.style.borderTop = '2px solid #1b3a6b';
                        targetBlock.style.borderBottom = '';
                    } else {
                        targetBlock.style.borderBottom = '2px solid #1b3a6b';
                        targetBlock.style.borderTop = '';
                    }
                } else if (!targetBlock && draggedBlock && canvas.children.length === 0) {
                    // If canvas is empty, allow dropping anywhere
                    canvas.classList.add('drag-over');
                }
            }
        });

        canvas.addEventListener('dragleave', (e) => {
            const targetBlock = e.target.closest('.question-block');
            if (targetBlock) {
                targetBlock.style.borderTop = '';
                targetBlock.style.borderBottom = '';
            } else if (e.target.id === 'canvas-content') {
                canvas.classList.remove('drag-over');
            }
        });

        canvas.addEventListener('dragend', (e) => {
            if (draggedBlock) {
                draggedBlock.classList.remove('dragging');
                draggedBlock = null;
            }
            // Clear all drag-over styles
            canvas.classList.remove('drag-over');
            document.querySelectorAll('.question-block').forEach(blockEl => {
                blockEl.style.borderTop = '';
                blockEl.style.borderBottom = '';
            });
        });

        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            canvas.classList.remove('drag-over');

            const targetBlockEl = e.target.closest('.question-block');
            
            // Handle dropping new blocks from palette
            if (e.dataTransfer.types.includes('application/json')) {
                const data = JSON.parse(e.dataTransfer.getData('application/json'));
                addBlock(data.template);
            } 
            // Handle reordering existing blocks
            else if (draggedBlock && targetBlockEl && draggedBlock !== targetBlockEl) {
                const draggedBlockId = draggedBlock.dataset.blockId;
                const targetBlockId = targetBlockEl.dataset.blockId;
                const fromIndex = blocks.findIndex(b => b.id === draggedBlockId);
                const toIndex = blocks.findIndex(b => b.id === targetBlockId);

                if (fromIndex > -1 && toIndex > -1) {
                    const [removed] = blocks.splice(fromIndex, 1);
                    
                    const bounding = targetBlockEl.getBoundingClientRect();
                    const offset = e.clientY - bounding.top;

                    if (offset < bounding.height / 2) {
                        // Drop above target
                        blocks.splice(toIndex, 0, removed);
                    } else {
                        // Drop below target
                        blocks.splice(toIndex + 1, 0, removed);
                    }
                    updateBlockOrder(); // Update sort_order for all blocks
                    saveHistory();
                    renderCanvas();
                    showSaveStatus();
                    
                    const blockOrderStr = blocks.map(b => b.id).join(',');
                    postAction("reorder_blocks", { block_order: blockOrderStr });
                }
            } else if (draggedBlock && !targetBlockEl && blocks.length === 0) {
                // Dropping an existing block onto an empty canvas
                // This case is unlikely if we handle adding new blocks and reordering correctly
                // But as a fallback, if a block is somehow dragged off and then dropped onto an empty canvas, just re-add it.
                const draggedBlockData = blocks.find(b => b.id === draggedBlock.dataset.blockId);
                if (draggedBlockData) {
                    blocks = [draggedBlockData];
                    updateBlockOrder();
                    saveHistory();
                    renderCanvas();
                    showSaveStatus();
                }
            }

            // Clear any visual feedback after drop
            document.querySelectorAll('.question-block').forEach(blockEl => {
                blockEl.style.borderTop = '';
                blockEl.style.borderBottom = '';
            });
        });
    }

    function updateBlockOrder() {
        blocks.forEach((block, index) => {
            block.output_options.sort_order = index;
        });
    }

    function getBlockTemplate(type) {
        const meta = builderStateQuestionTypes[type] || {};
        const timestamp = Date.now();

        return {
            id: `${pageId}__${type}_${timestamp}`,
            block_type: type,
            standard: {
                label: meta.default_label || 'New block',
                name: `${type}_${timestamp}`,
                required: false,
                help_text: '',
                source_prefix: '',
                placeholder: '',
                dropdown_choices: type === 'dropdown_select' || type === 'checkbox_group' ? ['Option 1', 'Option 2'] : [],
                static_content: '',
                static_variant: 'body'
            },
            logic_options: {
                visibility: 'always',
                depends_on_field: '',
                depends_on_value: ''
            },
            pricing_options: {
                enabled: false,
                mode: 'none',
                fixed_amount: 0,
                entered_key: '',
                rate: 0,
                quantity_key: '',
                percent_of_subtotal: 0
            },
            output_options: {
                include_in_output: true,
                output_label: '',
                group: 'General',
                sort_order: blocks.length,
                value_mode: 'show_value'
            }
        };
    }

    // Block Operations
    // Helper to post actions to backend
    async function postAction(action, data = {}) {
        const formData = new FormData();
        formData.append("action", action);
        // Include CSRF token if available on page
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            formData.append("csrf_token", csrfInput.value);
        }
        for (const key in data) {
            formData.append(key, data[key]);
        }

        try {
            await fetch(`/builder_beta/page/${pageId}`, {
                method: "POST",
                body: formData,
                redirect: "manual"
            });
            // We do a soft update by default, unless page reload is explicitly requested
        } catch (error) {
            console.error(`Error performing ${action}:`, error);
        }
    }

    function addBlock(template) {
        blocks.push(template);
        updateBlockOrder();
        saveHistory();
        renderCanvas();
        selectBlock(template.id);
        showSaveStatus();
        
        postAction("add_block", { block_type: template.block_type }).then(() => {
            // Need to reload to get the new block ID assigned by the backend
            setTimeout(() => location.reload(), 300);
        });
    }

    function deleteBlock(blockId) {
        const index = blocks.findIndex(b => b.id === blockId);
        if (index > -1) {
            blocks.splice(index, 1);
            updateBlockOrder();
            saveHistory();
            renderCanvas();
            propertiesContent.innerHTML = `
                <div class="properties-empty">
                    <div class="properties-empty-icon">🔲</div>
                    <p>Select a question to edit its properties</p>
                </div>
            `;
            selectedBlockId = null;
            showSaveStatus();
            
            postAction("delete_block", { block_id: blockId });
        }
    }

    function updateBlock(blockId, updates) {
        const index = blocks.findIndex(b => b.id === blockId);
        if (index > -1) {
            // Deep merge updates
            blocks[index] = deepMerge(blocks[index], updates);
            saveHistory();
            renderCanvas();
            if (selectedBlockId === blockId) {
                renderProperties();
            }
            showSaveStatus();
        }
    }

    function deepMerge(target, source) {
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key]) && typeof target[key] === 'object' && target[key] !== null) {
                    target[key] = deepMerge(target[key] || {}, source[key]);
                } else {
                    target[key] = source[key];
                }
            }
        }
        return target;
    }

    // Rendering
    function renderCanvas() {
        if (canvasContent) {
            if (blocks.length === 0) {
                canvasContent.innerHTML = `
                    <div class="canvas-empty">
                        <div class="canvas-empty-icon">📋</div>
                        <p>No questions yet. Click "+ Add Question" or drag a question type from the sidebar.</p>
                    </div>
                `;
                return;
            }
            
            canvasContent.innerHTML = blocks.map((block) => {
                const blockClass = `question-block ${block.id === selectedBlockId ? 'selected' : ''}`;
                return `
                    <div class="${blockClass}" 
                         data-block-id="${block.id}" 
                         data-type="${block.block_type}"
                         draggable="true">
                        <div class="question-block-header">
                            <span class="drag-handle">⠿</span>
                            <span class="block-type-badge">${block.block_type}</span>
                            <span class="block-title">${block.standard.label}</span>
                            <div class="block-actions">
                                <button type="button" class="block-action-btn edit" data-action="edit" title="Edit">✎</button>
                                <button type="button" class="block-action-btn delete" data-action="delete" title="Delete">🗑️</button>
                            </div>
                        </div>
                        <div class="question-block-body">
                            ${renderBlockPreview(block)}
                        </div>
                    </div>
                `;
            }).join('');

            attachCanvasBlockListeners();
        }
    }

    function attachCanvasBlockListeners() {
        canvasContent.querySelectorAll('.question-block').forEach(blockEl => {
            blockEl.addEventListener('click', (e) => {
                // Only select block if action button was not clicked
                if (!e.target.closest('.block-action-btn')) {
                    selectBlock(blockEl.dataset.blockId);
                }
            });

            blockEl.querySelector('.question-block-header').addEventListener('click', (e) => {
                // Allow drag handle to be dragged without triggering block selection
                if (!e.target.closest('.drag-handle')) {
                    selectBlock(blockEl.dataset.blockId);
                }
            });

            blockEl.querySelectorAll('.block-action-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent block selection when action button is clicked
                    const action = btn.dataset.action;
                    const blockId = blockEl.dataset.blockId;

                    if (action === 'edit') {
                        selectBlock(blockId);
                    } else if (action === 'delete') {
                        deleteBlock(blockId);
                    }
                });
            });
        });
    }

    function renderBlockPreview(block) {
        console.log('Rendering preview for block:', block.id, 'type:', block.block_type);
        switch (block.block_type) {
            case 'checkbox_group':
                const choices = block.standard.dropdown_choices || [];
                return `
                    <div class="checkbox-options">
                        ${choices.map((choice, i) => `
                            <div class="checkbox-option" style="margin-bottom: 5px;">
                                <input type="checkbox" id="${block.id}_opt_${i}" checked disabled>
                                <label for="${block.id}_opt_${i}" style="margin-left: 5px;">${choice}</label>
                            </div>
                        `).join('')}
                    </div>
                `;
            case 'text_input':
                return `
                    <div style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; color: #666;">
                        ${block.standard.placeholder || 'Enter text...'}
                    </div>
                `;
            case 'number_currency_input':
                return `
                    <div style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; color: #666;">
                        £${block.standard.placeholder || '0.00'}
                    </div>
                `;
            case 'dropdown_select':
                return `
                    <select style="width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
                        ${block.standard.dropdown_choices.map(choice => `<option>${choice}</option>`).join('')}
                    </select>
                `;
            case 'static_text_heading':
                const variantTag = block.standard.static_variant === 'heading' ? 'h3' :
                                     block.standard.static_variant === 'subheading' ? 'h4' : 'p';
                return `<${variantTag} style="margin: 0; color: #333;">${block.standard.static_content || block.standard.label}</${variantTag}>`;
            default:
                return '<p style="color: #666;">Preview not available</p>';
        }
    }

    // Pricing fields dynamic display based on mode
    // Defined as a named declaration so it is hoisted and available during init.
    // Also aliased to window so the inline onchange="updatePricingFields(...)" in the template can reach it.
    function updatePricingFields(mode) {
        const pricingFieldsDiv = document.getElementById("pricing-fields");
        if (!pricingFieldsDiv) return;

        let fieldsHtml = "";
        const block = blocks.find(b => b.id === selectedBlockId);
        const po = block ? block.pricing_options : {};

        switch (mode) {
            case "fixed":
                fieldsHtml = `
                    <div class="form-group">
                        <label>Fixed Amount (£)</label>
                        <input type="number" step="0.01" min="0" name="pricing_fixed_amount" value="${po.fixed_amount || 0}">
                    </div>
                `;
                break;
            case "entered":
                fieldsHtml = `
                    <div class="form-group">
                        <label>Reference Field</label>
                        <select name="pricing_entered_key">
                            <option value="">Select field...</option>
                            ${blocks.map(b => `<option value="${b.id}" ${b.id === po.entered_key ? "selected" : ""}>${b.standard.label}</option>`).join("")}
                        </select>
                    </div>
                `;
                break;
            case "quantity_rate":
                fieldsHtml = `
                    <div class="form-group">
                        <label>Quantity Field</label>
                        <select name="pricing_quantity_key">
                            <option value="">Select field...</option>
                            ${blocks.map(b => `<option value="${b.id}" ${b.id === po.quantity_key ? "selected" : ""}>${b.standard.label}</option>`).join("")}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Rate (£ per unit)</label>
                        <input type="number" step="0.01" min="0" name="pricing_rate" value="${po.rate || 0}">
                    </div>
                `;
                break;
            case "percent_subtotal":
                fieldsHtml = `
                    <div class="form-group">
                        <label>Percentage (%)</label>
                        <input type="number" step="0.01" min="0" max="100" name="pricing_percent_of_subtotal" value="${po.percent_of_subtotal || 0}">
                    </div>
                `;
                break;
            default:
                fieldsHtml = "";
                break;
        }
        pricingFieldsDiv.innerHTML = fieldsHtml;
        // Re-populate dynamic selects after innerHTML update
        updateDynamicSelectOptions();
    }
    // Expose to global scope so inline onchange="updatePricingFields(...)" in the template can reach it
    window.updatePricingFields = updatePricingFields;

    function renderProperties() {
        if (!propertiesContent) return; // Ensure propertiesContent exists

        if (!selectedBlockId) {
            propertiesContent.innerHTML = `
                <div class="properties-empty">
                    <div class="properties-empty-icon">🔲</div>
                    <p>Select a question to edit its properties</p>
                </div>
            `;
            return;
        }

        const block = blocks.find(b => b.id === selectedBlockId);
        if (!block) return;
        
        // The form in the macro now handles the submission.
        // We just need to ensure the correct block data is passed to the macro.
        // This function will be removed or repurposed if rendering properties dynamically via JS becomes complex.
        // For now, assume Flask renders this via the macro.
        // The main action will be to update the form fields based on the selected block.

        // Manually update the form elements in the properties panel
        document.querySelector('#block-properties-form input[name="block_id"]').value = block.id;
        document.querySelector('#prop-fields input[name="standard_label"]').value = block.standard.label;
        document.querySelector('#prop-fields input[name="standard_name"]').value = block.standard.name;
        document.querySelector('#prop-fields textarea[name="standard_help_text"]').value = block.standard.help_text;
        document.querySelector('#prop-fields input[name="standard_required"]').checked = block.standard.required;

        if (block.block_type === 'text_input' || block.block_type === 'number_currency_input') {
            const placeholderInput = document.querySelector('#prop-fields input[name="standard_placeholder"]');
            if (placeholderInput) placeholderInput.value = block.standard.placeholder;
        } else if (block.block_type === 'dropdown_select' || block.block_type === 'checkbox_group') {
            const choicesTextarea = document.querySelector('#prop-fields textarea[name="standard_dropdown_choices"]');
            if (choicesTextarea) choicesTextarea.value = block.standard.dropdown_choices.join('\n');
            const sourcePrefixInput = document.querySelector('#prop-fields input[name="standard_source_prefix"]');
            if (sourcePrefixInput) sourcePrefixInput.value = block.standard.source_prefix;
        } else if (block.block_type === 'static_text_heading') {
            const contentTextarea = document.querySelector('#prop-fields textarea[name="standard_static_content"]');
            if (contentTextarea) contentTextarea.value = block.standard.static_content;
            const variantSelect = document.querySelector('#prop-fields select[name="standard_static_variant"]');
            if (variantSelect) variantSelect.value = block.standard.static_variant;
        }

        // Logic Options
        document.querySelector('select[name="logic_visibility"]').value = block.logic_options.visibility;
        const logicConditionsDiv = document.getElementById('logic-conditions');
        if (logicConditionsDiv) {
            logicConditionsDiv.style.display = block.logic_options.visibility === 'conditional' ? 'block' : 'none';
        }
        document.querySelector('select[name="logic_depends_on_field"]').value = block.logic_options.depends_on_field;
        document.querySelector('input[name="logic_depends_on_value"]').value = block.logic_options.depends_on_value;

        // Pricing Options
        document.querySelector('input[name="pricing_enabled"]').checked = block.pricing_options.enabled;
        document.querySelector('select[name="pricing_mode"]').value = block.pricing_options.mode;
        updatePricingFields(block.pricing_options.mode); // Re-renders dynamic pricing fields into DOM

        // These inputs are conditionally rendered by the pricing mode — guard against null
        const elFixedAmount = document.querySelector('input[name="pricing_fixed_amount"]');
        if (elFixedAmount) elFixedAmount.value = block.pricing_options.fixed_amount;
        const elEnteredKey = document.querySelector('select[name="pricing_entered_key"]');
        if (elEnteredKey) elEnteredKey.value = block.pricing_options.entered_key;
        const elQuantityKey = document.querySelector('select[name="pricing_quantity_key"]');
        if (elQuantityKey) elQuantityKey.value = block.pricing_options.quantity_key;
        const elRate = document.querySelector('input[name="pricing_rate"]');
        if (elRate) elRate.value = block.pricing_options.rate;
        const elPercentSubtotal = document.querySelector('input[name="pricing_percent_of_subtotal"]');
        if (elPercentSubtotal) elPercentSubtotal.value = block.pricing_options.percent_of_subtotal;

        // Output Options
        document.querySelector('input[name="output_include_in_output"]').checked = block.output_options.include_in_output;
        document.querySelector('input[name="output_label"]').value = block.output_options.output_label;
        document.querySelector('input[name="output_group"]').value = block.output_options.group;
        document.querySelector('select[name="output_value_mode"]').value = block.output_options.value_mode;

        // Update any dynamic options for logic_depends_on_field / pricing_entered_key / pricing_quantity_key
        updateDynamicSelectOptions();
    }

    function updateDynamicSelectOptions() {
        const logicDependsOnFieldSelect = document.querySelector('select[name="logic_depends_on_field"]');
        const pricingEnteredKeySelect = document.querySelector('select[name="pricing_entered_key"]');
        const pricingQuantityKeySelect = document.querySelector('select[name="pricing_quantity_key"]');

        const currentBlock = blocks.find(b => b.id === selectedBlockId);

        // Helper to populate select elements
        function populateSelect(selectElement, selectedValue, filterCurrentBlock = false) {
            if (!selectElement) return;
            // erase if already selected, otherwise retain selection if option exists.
            for (let i = selectElement.options.length - 1; i >= 0; i--) {
                if (selectElement.options[i].value !== "") {
                    selectElement.remove(i);
                }
            }
            
            blocks.forEach(block => {
                if (filterCurrentBlock && block.id === currentBlock.id) return;

                const option = document.createElement("option");
                option.value = block.id;
                option.textContent = block.standard.label;
                if (block.id === selectedValue) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        }

        // Populate Logic -> Depends on Field
        populateSelect(logicDependsOnFieldSelect, currentBlock.logic_options.depends_on_field, true);

        // Populate Pricing -> Entered Key
        populateSelect(pricingEnteredKeySelect, currentBlock.pricing_options.entered_key);

        // Populate Pricing -> Quantity Key
        populateSelect(pricingQuantityKeySelect, currentBlock.pricing_options.quantity_key);
    }

    // Event Listeners
    function setupEventListeners() {
        // Page selection
        if (pageSelect) {
            pageSelect.addEventListener("change", (e) => {
                window.location.href = `/builder_beta/page/${e.target.value}`; // Redirect to new page editor
            });
        }

        // Add block button — show type picker dropdown
        if (btnAddBlock) {
            btnAddBlock.addEventListener("click", () => {
                showTypePicker(btnAddBlock);
            });
        }

        // Save button for properties form
        // The form itself handles submission via the macro. We just need to trigger a re-render/update if needed.
        const blockPropertiesForm = document.getElementById("block-properties-form");
        if (blockPropertiesForm) {
            blockPropertiesForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                
                const formData = new FormData(blockPropertiesForm);
                const actionUrl = blockPropertiesForm.getAttribute("action");
                
                try {
                    await fetch(actionUrl, {
                        method: "POST",
                        body: formData,
                        redirect: "manual" // Don't follow the redirect
                    });

                    // Option A: Sync local blocks array with submitted form values
                    const blockId = formData.get("block_id");
                    const block = blocks.find(b => b.id === blockId);
                    if (block) {
                        // Standard properties
                        block.standard.label        = (formData.get("standard_label") || block.standard.label).trim();
                        block.standard.name         = (formData.get("standard_name") || block.standard.name).trim();
                        block.standard.help_text    = (formData.get("standard_help_text") || "").trim();
                        block.standard.source_prefix = (formData.get("standard_source_prefix") || "").trim();
                        block.standard.placeholder  = (formData.get("standard_placeholder") || "").trim();
                        block.standard.required     = formData.get("standard_required") === "on";
                        block.standard.static_content = (formData.get("standard_static_content") || "").trim();
                        block.standard.static_variant = (formData.get("standard_static_variant") || "body").trim();
                        const rawChoices = formData.get("standard_dropdown_choices") || "";
                        block.standard.dropdown_choices = rawChoices.split("\n").map(c => c.trim()).filter(Boolean);

                        // Logic options
                        block.logic_options.visibility       = (formData.get("logic_visibility") || "always").trim();
                        block.logic_options.depends_on_field = (formData.get("logic_depends_on_field") || "").trim();
                        block.logic_options.depends_on_value = (formData.get("logic_depends_on_value") || "").trim();

                        // Pricing options
                        const pricingMode = (formData.get("pricing_mode") || "none").trim();
                        block.pricing_options.enabled           = formData.get("pricing_enabled") === "on";
                        block.pricing_options.mode              = pricingMode;
                        block.pricing_options.fixed_amount      = parseFloat(formData.get("pricing_fixed_amount")) || 0;
                        block.pricing_options.entered_key       = (formData.get("pricing_entered_key") || "").trim();
                        block.pricing_options.quantity_key      = (formData.get("pricing_quantity_key") || "").trim();
                        block.pricing_options.rate              = parseFloat(formData.get("pricing_rate")) || 0;
                        block.pricing_options.percent_of_subtotal = parseFloat(formData.get("pricing_percent_of_subtotal")) || 0;

                        // Output options
                        block.output_options.include_in_output = formData.get("output_include_in_output") === "on";
                        block.output_options.output_label      = (formData.get("output_label") || block.standard.label).trim();
                        block.output_options.group             = (formData.get("output_group") || "General").trim();
                        block.output_options.value_mode        = (formData.get("output_value_mode") || "show_value").trim();

                        saveHistory();
                        renderCanvas();
                        renderProperties();
                    }
                    
                    showSaveStatus();
                } catch (error) {
                    console.error("Error saving block:", error);
                    alert("Failed to save block.");
                }
            });
        }

        // Undo/Redo
        if (btnUndo) btnUndo.addEventListener("click", undo);
        if (btnRedo) btnRedo.addEventListener("click", redo);

        // Preview buttons
        if (btnPreviewFloat) {
            btnPreviewFloat.addEventListener("click", () => {
                window.open(`/builder_beta/runtime_render/${pageId}`, "_blank");
            });
        }
        const btnPreviewHeader = document.getElementById("btn-preview");
        if (btnPreviewHeader) {
            btnPreviewHeader.addEventListener("click", () => {
                window.open(`/builder_beta/runtime_payload_json/${pageId}`, "_blank");
            });
        }

        // Keyboard shortcuts
        document.addEventListener("keydown", (e) => {
            if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
            
            if (e.key === "Delete" && selectedBlockId) {
                e.preventDefault();
                deleteBlock(selectedBlockId);
            }
            if ((e.ctrlKey || e.metaKey) && e.key === "z") {
                e.preventDefault();
                undo();
            }
            if ((e.ctrlKey || e.metaKey) && e.key === "y") {
                e.preventDefault();
                redo();
            }
        });

        // Toggle collapsible sections in properties panel
        document.querySelectorAll(".prop-section-header").forEach(header => {
            header.addEventListener("click", (e) => {
                const section = header.closest(".prop-section");
                if (section) {
                    section.classList.toggle("collapsed");
                }
            });
        });

        // Logic visibility toggle
        const logicVisibilitySelect = document.querySelector('select[name="logic_visibility"]');
        if (logicVisibilitySelect) {
            logicVisibilitySelect.addEventListener("change", (e) => {
                const logicConditionsDiv = document.getElementById("logic-conditions");
                if (logicConditionsDiv) {
                    logicConditionsDiv.style.display = e.target.value === "conditional" ? "block" : "none";
                }
            });
        }

        // Pricing enabled toggle
        const pricingEnabledCheckbox = document.querySelector('input[name="pricing_enabled"]');
        if (pricingEnabledCheckbox) {
            pricingEnabledCheckbox.addEventListener("change", (e) => {
                const pricingFieldsDiv = document.getElementById("pricing-fields");
                if (pricingFieldsDiv) {
                    if (e.target.checked) {
                        pricingFieldsDiv.classList.add("active");
                    } else {
                        pricingFieldsDiv.classList.remove("active");
                    }
                }
            });
        }
    }



    // History Management
    function saveHistory() {
        history = history.slice(0, historyIndex + 1);
        history.push(JSON.stringify(blocks));
        historyIndex = history.length - 1;
        updateUndoRedoButtons();
    }

    function undo() {
        if (historyIndex > 0) {
            historyIndex--;
            blocks = JSON.parse(history[historyIndex]);
            renderCanvas();
            renderProperties();
            showSaveStatus("Undo", "#17a2b8");
        }
        updateUndoRedoButtons();
    }

    function redo() {
        if (historyIndex < history.length - 1) {
            historyIndex++;
            blocks = JSON.parse(history[historyIndex]);
            renderCanvas();
            renderProperties();
            showSaveStatus("Redo", "#17a2b8");
        }
        updateUndoRedoButtons();
    }

    function updateUndoRedoButtons() {
        if (btnUndo) btnUndo.disabled = historyIndex <= 0;
        if (btnRedo) btnRedo.disabled = historyIndex >= history.length - 1;
    }

    // UI Helpers
    function selectBlock(blockId) {
        selectedBlockId = blockId;
        renderCanvas(); // Re-render canvas to update selection highlight
        renderProperties(); // Re-render properties panel for selected block
    }

    // No longer needed as toggleSection is in the macro
    // function toggleSection(sectionId) {
    //     const section = document.getElementById(sectionId);
    //     section.classList.toggle('collapsed');
    // }

    // Type picker modal — shows clickable list of available question types
    function showTypePicker(anchorEl) {
        // Remove existing picker if any
        const existing = document.getElementById('type-picker-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'type-picker-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,.35); z-index: 10000;
            display: flex; align-items: center; justify-content: center;
        `;
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });

        const picker = document.createElement('div');
        picker.style.cssText = `
            background: #fff; border-radius: 8px; padding: 1.5rem;
            min-width: 300px; max-width: 420px; box-shadow: 0 4px 20px rgba(0,0,0,.25);
        `;
        picker.innerHTML = `
            <h3 style="margin:0 0 .75rem;font-size:1.1rem;">Add Question</h3>
            <p style="margin:0 0 .75rem;font-size:.85rem;color:#666;">Select a question type to add:</p>
            <div style="display:flex;flex-direction:column;gap:.4rem;">
                ${Object.entries(builderStateQuestionTypes).map(([type, meta]) => `
                    <button type="button" class="type-picker-btn" data-type="${type}"
                        style="display:flex;align-items:center;gap:.6rem;padding:.55rem .75rem;
                               border:1px solid #ddd;border-radius:6px;background:#fafafa;
                               cursor:pointer;text-align:left;font-size:.9rem;
                               transition:background .15s;">
                        <span style="font-size:1.2rem;">${meta.icon || '?'}</span>
                        <div>
                            <div style="font-weight:600;">${meta.label}</div>
                            <div style="font-size:.78rem;color:#888;">${meta.description || ''}</div>
                        </div>
                    </button>
                `).join('')}
            </div>
            <button type="button" class="type-picker-cancel"
                style="display:block;width:100%;margin-top:.75rem;padding:.4rem;
                       border:1px solid #ccc;border-radius:4px;background:#fff;
                       cursor:pointer;font-size:.85rem;color:#666;">Cancel</button>
        `;

        picker.querySelectorAll('.type-picker-btn').forEach(btn => {
            btn.addEventListener('mouseenter', () => btn.style.background = '#eef');
            btn.addEventListener('mouseleave', () => btn.style.background = '#fafafa');
            btn.addEventListener('click', () => {
                addBlock(getBlockTemplate(btn.dataset.type));
                overlay.remove();
            });
        });
        picker.querySelector('.type-picker-cancel').addEventListener('click', () => overlay.remove());

        overlay.appendChild(picker);
        document.body.appendChild(overlay);
    }

    function showSaveStatus(message = "Saved", color = "#28a745") {
        if (saveStatus) {
            saveStatus.textContent = message;
            saveStatus.style.backgroundColor = color;
            saveStatus.classList.add("visible");
            setTimeout(() => saveStatus.classList.remove("visible"), 2000);
        }
    }

    // Admin actions (Publish, Rollback) - already handled in form.html script
    // These buttons are outside the scope of builder.js, handled in form.html directly

});

// Global utility for toggling sections (used by macros)
window.toggleSection = function(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.toggle("collapsed");
    }
};

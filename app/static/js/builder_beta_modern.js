/*=====================================================================
  ModernBuilderBeta – main UI class for the Modern Builder Beta
  ---------------------------------------------------------------
  • Drag‑and‑drop from the component palette onto the canvas
  • Click‑to‑select a block, open its property panel
  • Edit / delete blocks via the block‑header controls
  • Save form / block data via the backend API
  • Toast notifications for user feedback
=====================================================================*/

class ModernBuilderBeta {
    /**
     * @param {Object} [options]          Options object.
     * @param {string} [options.csrfToken]   CSRF token (meta tag or hidden input).
     * @param {string} [options.apiBase]     Base URL for the builder API (default: '/api/builder_beta').
     */
    constructor(options = {}) {
        // -----------------------------------------------------------------
        // 1️⃣  Store configuration values – fall back to DOM when missing.
        // -----------------------------------------------------------------
        this.csrfToken =
            options.csrfToken ||
            document.querySelector('meta[name="csrf-token"]')?.content ||
            '';
        this.apiBase = options.apiBase || '/api/builder_beta';

        // -----------------------------------------------------------------
        // 2️⃣  Runtime state.
        // -----------------------------------------------------------------
        this.selectedBlockId = null;   // id of the currently selected block
        this.isDirty = false;         // form / canvas has unsaved changes

        // -----------------------------------------------------------------
        // 3️⃣  Initialise the UI – all DOM interactions are performed here.
        // -----------------------------------------------------------------
        this.init();
    }

    /* -----------------------------------------------------------------
     *  init() – entry point that wires all UI events.
     * ----------------------------------------------------------------- */
    init() {
        this.setupDragDrop();          // palette → canvas
        this.setupCanvasClicks();      // click → select / deselect block
        this.setupBlockControls();     // edit / delete buttons inside blocks
        this.setupSaveHandler();       // global “Save” button
    }

    /* -----------------------------------------------------------------
     *  DRAG‑AND‑DROP
     * ----------------------------------------------------------------- */
    setupDragDrop() {
        const paletteItems = document.querySelectorAll('.component-item');
        const canvas = document.getElementById('builder-canvas');

        if (!canvas) {
            console.warn('Canvas element not found – drag‑and‑drop disabled.');
            return;
        }

        // ---- palette items ------------------------------------------------
        paletteItems.forEach(item => {
            item.addEventListener('dragstart', e => {
                const blockType = item.dataset.blockType || item.dataset.type;
                e.dataTransfer.setData('text/plain', blockType);
                item.classList.add('dragging');
            });

            item.addEventListener('dragend', () => item.classList.remove('dragging'));
        });

        // ---- canvas listeners --------------------------------------------
        canvas.addEventListener('dragover', e => {
            e.preventDefault();                 // necessary for drop to fire
            canvas.classList.add('drag-over');   // visual cue for drop zone
        });

        canvas.addEventListener('dragleave', () => {
            canvas.classList.remove('drag-over');
        });

        canvas.addEventListener('drop', e => {
            e.preventDefault();
            canvas.classList.remove('drag-over');

            const blockType = e.dataTransfer.getData('text/plain');
            if (blockType) {
                this.createBlock(blockType);
            }
        });
    }

    /* -----------------------------------------------------------------
     *  CANVAS CLICK HANDLING
     * ----------------------------------------------------------------- */
    setupCanvasClicks() {
        document.addEventListener('click', e => {
            const block = e.target.closest('.builder-block');
            if (block) {
                const blockId = block.dataset.blockId;
                if (blockId) this.selectBlock(blockId);
                return;
            }

            // Click outside any block → clear selection
            if (!e.target.closest('.properties-sidebar')) {
                this.deselectBlock();
            }
        });
    }

    /* -----------------------------------------------------------------
     *  BLOCK‑LEVEL CONTROLS (edit / delete)
     * ----------------------------------------------------------------- */
    setupBlockControls() {
        document.addEventListener('click', e => {
            const editBtn = e.target.closest('[title="Edit"]');
            const deleteBtn = e.target.closest('[title="Delete"]');

            if (editBtn) {
                const block = editBtn.closest('.builder-block');
                if (block) this.editBlock(block.dataset.blockId);
            }

            if (deleteBtn) {
                const block = deleteBtn.closest('.builder-block');
                if (block) this.deleteBlock(block.dataset.blockId);
            }
        });
    }

    /* -----------------------------------------------------------------
     *  GLOBAL SAVE BUTTON
     * ----------------------------------------------------------------- */
    setupSaveHandler() {
        const saveBtn = document.querySelector('.btn-save, [data-action="save"]');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveForm());
        }
    }

    /* -----------------------------------------------------------------
     *  BLOCK CREATION
     * ----------------------------------------------------------------- */
    async createBlock(blockType) {
        try {
            const response = await this.ajax(
                `${this.apiBase}/create_block`,
                'POST',
                { block_type: blockType }
            );

            if (response && response.block_id) {
                this.addBlockToCanvas(response);
                this.selectBlock(response.block_id);
                this.isDirty = true;
            }
        } catch (err) {
            console.error('Failed to create block:', err);
            this.showToast('Failed to create block', 'error');
        }
    }

    /* -----------------------------------------------------------------
     *  INSERT BLOCK INTO THE CANVAS
     * ----------------------------------------------------------------- */
    addBlockToCanvas(blockData) {
        // In a production app this would render a server‑side partial.
        // For now we fetch the pre‑rendered HTML fragment.
        this.fetchBlockHtml(blockData.block_id).then(html => {
            const canvasContent = document.querySelector('.builder-canvas-content');
            const emptyMsg = canvasContent?.querySelector('.empty-canvas-message');
            if (emptyMessage) emptyMessage.remove();

            canvasContent.insertAdjacentHTML('beforeend', html);
        });
    }

    /* -----------------------------------------------------------------
     *  FETCH BLOCK HTML FROM THE SERVER
     * ----------------------------------------------------------------- */
    async fetchBlockHtml(blockId) {
        const response = await this.ajax(`${this.apiBase}/block/${blockId}`, 'GET');
        return response.html || '';
    }

    /* -----------------------------------------------------------------
     *  SELECT / DESELECT BLOCK
     * ----------------------------------------------------------------- */
    selectBlock(blockId) {
        this.deselectBlock();                 // clear any previous selection
        this.selectedBlockId = blockId;

        const block = document.querySelector(`.builder-block[data-block-id="${blockId}"]`);
        if (block) block.classList.add('selected');

        this.loadBlockProperties(blockId);
    }

    deselectBlock() {
        if (this.selectedBlockId) {
            const prev = document.querySelector(`.builder-block[data-block-id="${this.selectedBlockId}"]`);
            if (prev) prev.classList.remove('selected');
            this.selectedBlockId = null;
        }

        const panel = document.querySelector('.properties-content');
        if (panel) {
            panel.innerHTML = '<p class="no-selection">Select a block to edit its properties</p>';
        }
    }

    /* -----------------------------------------------------------------
     *  LOAD PROPERTIES FOR A BLOCK
     * ----------------------------------------------------------------- */
    async loadBlockProperties(blockId) {
        try {
            const data = await this.ajax(`${this.apiBase}/block/${blockId}`, 'GET');
            const panel = document.querySelector('.properties-content');

            if (panel && data?.properties_html) {
                panel.innerHTML = data.properties_html;
                this.attachPropertyFormHandlers(blockId);
            }
        } catch (err) {
            console.error('Failed to load properties:', err);
        }
    }

    /* -----------------------------------------------------------------
     *  PROPERTY FORM HANDLERS
     * ----------------------------------------------------------------- */
    attachPropertyFormHandlers(blockId) {
        const form = document.querySelector('.properties-form');
        if (!form) return;

        form.addEventListener('submit', e => {
            e.preventDefault();
            this.saveBlockProperties(blockId, new FormData(form));
        });
    }

    /* -----------------------------------------------------------------
     *  SAVE BLOCK PROPERTIES (PUT request)
     * ----------------------------------------------------------------- */
    async saveBlockProperties(blockId, formData) {
        try {
            const data = Object.fromEntries(formData.entries());
            const response = await this.ajax(
                `${this.apiBase}/block/${blockId}`,
                'PUT',
                data
            );

            if (response.success) {
                this.updateBlockPreview(blockId, response.html);
                this.isDirty = true;
                this.showToast('Block updated', 'success');
            }
        } catch (err) {
            console.error('Failed to save properties:', err);
            this.showToast('Failed to save', 'error');
        }
    }

    /* -----------------------------------------------------------------
     *  UPDATE BLOCK PREVIEW AFTER A SUCCESSFUL SAVE
     * ----------------------------------------------------------------- */
    updateBlockPreview(blockId, html) {
        const block = document.querySelector(`.builder-block[data-block-id="${blockId}"]`);
        if (block && html) block.outerHTML = html;
    }

    /* -----------------------------------------------------------------
     *  BLOCK DELETION
     * ----------------------------------------------------------------- */
    async deleteBlock(blockId) {
        if (!confirm('Are you sure you want to delete this block?')) return;

        try {
            const response = await this.ajax(
                `${this.apiBase}/block/${blockId}`,
                'DELETE'
            );

            if (response.success) {
                const block = document.querySelector(`.builder-block[data-block-id="${blockId}"]`);
                if (block) block.remove();

                this.isDirty = true;
                this.deselectBlock();
                this.showToast('Block deleted', 'success');
            }
        } catch (err) {
            console.error('Failed to delete block:', err);
            this.showToast('Failed to delete', 'error');
        }
    }

    /* -----------------------------------------------------------------
     *  FORM SUBMISSION
     * ----------------------------------------------------------------- */
    async saveForm() {
        try {
            const response = await this.ajax(`${this.apiBase}/save`, 'POST', {});
            if (response.success) {
                this.isDirty = false;
                this.showToast('Form saved', 'success');
            }
        } catch (err) {
            console.error('Failed to save:', err);
            this.showToast('Failed to save', 'error');
        }
    }

    /* -----------------------------------------------------------------
     *  AJAX HELPER – centralised error handling & JSON parsing
     * ----------------------------------------------------------------- */
    async ajax(url, method = 'GET', data = null) {
        const opts = {
            method,
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            opts.body = JSON.stringify(data);
        }

        const response = await fetch(url, opts);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    /* -----------------------------------------------------------------
     *  TOAST NOTIFICATIONS
     * ----------------------------------------------------------------- */
    showToast(message, type = 'info') {
        // Ensure a container exists – if not, create one.
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 4px;
            color: white;
            font-size: 14px;
            z-index: 1000;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s;
        `;

        container.appendChild(toast);
        requestAnimationFrame(() => (toast.style.opacity = '1'));

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

/* -----------------------------------------------------------------
 *  Initialise the class when the DOM is ready.
 * ----------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    new ModernBuilderBeta({
        csrfToken: document.querySelector('meta[name="csrf-token"]')?.content || '',
        apiBase: '/api/builder_beta'
    });
});
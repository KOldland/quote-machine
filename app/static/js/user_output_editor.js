(function () {
  'use strict';

  const BLOCK_TYPES = {
    notes: { label: 'Notes', icon: '📝' },
    calculator: { label: 'Calculator', icon: '🧮' },
    image_group: { label: 'Image Group', icon: '🖼️' },
    image: { label: 'Image', icon: '🖼️' },
    form: { label: 'Form', icon: '📋' },
  };

  let blocks = [];
  let activeBlockId = null;
  let sortableInstance = null;

  function generateId() {
    return 'block_' + Math.random().toString(36).slice(2, 9);
  }

  function getBlockEl(blockId) {
    return document.querySelector(`.editor-block[data-block-id="${blockId}"]`);
  }

  function createBlockEl(block) {
    const wrapper = document.createElement('div');
    wrapper.className = 'editor-block';
    wrapper.dataset.blockId = block.id;
    wrapper.dataset.blockType = block.type;

    const typeInfo = BLOCK_TYPES[block.type] || { label: block.type, icon: '📄' };
    const snapshot = block.snapshot || {};
    const settings = block.settings || {};
    const flags = block.flags || {};

    wrapper.innerHTML = `
      <div class="editor-block__header">
        <span class="editor-block__drag-handle" title="Drag to reorder">☰</span>
        <span class="editor-block__type-label">${typeInfo.icon} ${typeInfo.label}</span>
        <span class="editor-block__source-dot ${flags.source_dirty ? 'editor-block__source-dot--dirty' : ''} ${flags.editor_dirty ? 'editor-block__source-dot--editor' : ''}" title=""></span>
        <button class="editor-block__remove" title="Remove block">&times;</button>
      </div>
      <div class="editor-block__content" contenteditable="true" data-placeholder="Type here...">
        ${renderBlockContent(block)}
      </div>
      <div class="editor-block__settings">
        <label>Margin T <input type="number" data-setting="margin_top" value="${settings.margin_top || 8}" min="0" max="40"></label>
        <label>Margin B <input type="number" data-setting="margin_bottom" value="${settings.margin_bottom || 8}" min="0" max="40"></label>
        <label>Padding <input type="number" data-setting="padding" value="${settings.padding || 12}" min="0" max="40"></label>
        <label>Align
          <select data-setting="alignment">
            <option value="left" ${settings.alignment === 'left' ? 'selected' : ''}>Left</option>
            <option value="center" ${settings.alignment === 'center' ? 'selected' : ''}>Center</option>
            <option value="right" ${settings.alignment === 'right' ? 'selected' : ''}>Right</option>
          </select>
        </label>
      </div>
    `;

    wrapper.querySelector('.editor-block__remove').addEventListener('click', () => {
      removeBlock(block.id);
    });

    const contentEl = wrapper.querySelector('.editor-block__content');
    contentEl.addEventListener('input', () => {
      block.editor_overrides = { ...(block.editor_overrides || {}), content: contentEl.innerHTML };
      block.flags = block.flags || {};
      block.flags.editor_dirty = true;
      wrapper.querySelector('.editor-block__source-dot').classList.add('editor-block__source-dot--editor');
    });

    wrapper.querySelectorAll('[data-setting]').forEach(input => {
      input.addEventListener('change', () => {
        block.settings = block.settings || {};
        block.settings[input.dataset.setting] = input.type === 'number' ? parseInt(input.value, 10) || 0 : input.value;
      });
    });

    wrapper.addEventListener('click', (e) => {
      if (e.target.closest('.editor-block__settings') || e.target.closest('.editor-block__header')) return;
      setActiveBlock(block.id);
    });

    return wrapper;
  }

  function renderBlockContent(block) {
    const snapshot = block.snapshot || {};
    switch (block.type) {
      case 'form':
        const label = snapshot.label || '';
        const value = snapshot.value || '';
        return label ? `<strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}` : escapeHtml(value);
      case 'calculator':
        const groups = snapshot.groups || [];
        let html = '<div class="calc-summary"><table class="calc-table"><thead><tr><th>Item</th><th>Total</th><th>Group</th></tr></thead><tbody>';
        groups.forEach(g => {
          (g.items || []).forEach(item => {
            html += `<tr><td>${escapeHtml(item.output_title || '')}</td><td>${item.line_total?.toFixed(2) || '0.00'}</td><td>${escapeHtml(g.name || '')}</td></tr>`;
          });
        });
        html += `</tbody></table><p><strong>Grand Total: ${snapshot.grand_total?.toFixed(2) || '0.00'}</strong></p></div>`;
        return html;
      case 'notes':
        return snapshot.content || '<p>Start typing notes...</p>';
      case 'image':
        const url = snapshot.url || '';
        return url ? `<img src="${escapeHtml(url)}" style="max-width:100%; height:auto;" />` : '<p>No image selected</p>';
      case 'image_group':
        const images = snapshot.images || [];
        if (!images.length) return '<p>No images in group</p>';
        const cols = snapshot.columns || 2;
        let grid = `<div style="display:grid; grid-template-columns: repeat(${cols}, 1fr); gap:8px;">`;
        images.forEach(img => {
          grid += `<div><img src="${escapeHtml(img.url || '')}" style="width:100%; height:auto;" /></div>`;
        });
        grid += '</div>';
        return grid;
      default:
        return '';
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function addBlock(blockData) {
    const block = {
      id: blockData.id || generateId(),
      type: blockData.type,
      snapshot: blockData.snapshot || {},
      editor_overrides: blockData.editor_overrides || {},
      flags: blockData.flags || { source_dirty: false, editor_dirty: false },
      settings: blockData.settings || { margin_top: 8, margin_bottom: 8, padding: 12, alignment: 'left' },
    };
    blocks.push(block);
    const el = createBlockEl(block);
    const container = document.getElementById('blocksContainer');
    const empty = container.querySelector('.editor-canvas__empty');
    if (empty) empty.remove();
    container.appendChild(el);
    setActiveBlock(block.id);
    return block;
  }

  function removeBlock(blockId) {
    blocks = blocks.filter(b => b.id !== blockId);
    const el = getBlockEl(blockId);
    if (el) el.remove();
    if (activeBlockId === blockId) activeBlockId = null;
    updateSourceColumn();
    const container = document.getElementById('blocksContainer');
    if (!container.querySelector('.editor-block')) {
      container.innerHTML = '<p class="editor-canvas__empty">Add blocks from the right panel to get started.</p>';
    }
  }

  function setActiveBlock(blockId) {
    activeBlockId = blockId;
    document.querySelectorAll('.editor-block').forEach(el => el.style.outline = '');
    const el = getBlockEl(blockId);
    if (el) {
      el.style.outline = '2px solid #0d6efd';
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    updateSourceColumn();
  }

  function updateSourceColumn() {
    const container = document.getElementById('sourceColumnContent');
    if (!activeBlockId) {
      container.innerHTML = '<p class="editor-source-column__placeholder">Select a block to see its source mapping.</p>';
      return;
    }
    const block = blocks.find(b => b.id === activeBlockId);
    if (!block || block.type !== 'form') {
      container.innerHTML = '<p class="editor-source-column__placeholder">Source mapping is only available for Form blocks.</p>';
      return;
    }
    const snapshot = block.snapshot || {};
    const flags = block.flags || {};
    container.innerHTML = `
      <div class="editor-source-item">
        <div class="editor-source-item__header">
          <span class="editor-source-item__dot ${flags.source_dirty ? 'editor-source-item__dot--dirty' : ''}"></span>
          <span class="editor-source-item__type">Form Block</span>
        </div>
        <div><strong>Page:</strong> ${escapeHtml(block.source_page || 'N/A')}</div>
        <div><strong>Block:</strong> ${escapeHtml(block.source_block_id || 'N/A')}</div>
        <div><strong>Label:</strong> ${escapeHtml(snapshot.label || 'N/A')}</div>
        <div><strong>Value:</strong> ${escapeHtml(snapshot.value || 'N/A')}</div>
        ${flags.source_dirty ? '<div style="color:#dc3545; font-size:0.8rem;">Source changed since snapshot</div>' : ''}
        ${flags.editor_dirty ? '<div style="color:#d39e00; font-size:0.8rem;">Edited in quote editor</div>' : ''}
      </div>
    `;
  }

  function initSortable() {
    const canvas = document.getElementById('blocksContainer');
    if (sortableInstance) sortableInstance.destroy();
    sortableInstance = Sortable.create(canvas, {
      animation: 150,
      handle: '.editor-block__drag-handle',
      onEnd: (evt) => {
        const newOrder = [...canvas.querySelectorAll('.editor-block')].map(el => el.dataset.blockId);
        blocks = newOrder.map(id => blocks.find(b => b.id === id)).filter(Boolean);
      }
    });
  }

  function initToolbar() {
    const toolbar = document.getElementById('editorToolbar');
    toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-command]');
      if (!btn) return;
      const command = btn.dataset.command;
      const value = btn.dataset.value || null;
      document.execCommand(command, false, value);
      const active = document.querySelector('.editor-block__content:focus');
      if (active) {
        const blockEl = active.closest('.editor-block');
        if (blockEl) {
          const blockId = blockEl.dataset.blockId;
          const block = blocks.find(b => b.id === blockId);
          if (block) {
            block.editor_overrides = { ...(block.editor_overrides || {}), content: active.innerHTML };
            block.flags = block.flags || {};
            block.flags.editor_dirty = true;
            blockEl.querySelector('.editor-block__source-dot').classList.add('editor-block__source-dot--editor');
          }
        }
      }
    });

    document.getElementById('insertImageToolbarBtn').addEventListener('click', () => {
      openGalleryModal('image');
    });
  }

  async function openGalleryModal(mode) {
    const modal = document.getElementById('imageGalleryModal');
    const grid = document.getElementById('galleryGrid');
    modal.style.display = 'flex';
    grid.innerHTML = '<p>Loading images...</p>';
    try {
      const res = await fetch('/quote_editor/images');
      const data = await res.json();
      const images = data.images || [];
      if (!images.length) {
        grid.innerHTML = '<p>No images available. Upload one below.</p>';
        return;
      }
      grid.innerHTML = images.map(img => `
        <div class="gallery-item" data-url="${escapeHtml(img.url)}" data-filename="${escapeHtml(img.filename || '')}">
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.original_name || img.filename)}">
          <div class="gallery-item__name">${escapeHtml(img.original_name || img.filename)}</div>
        </div>
      `).join('');
      grid.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', () => {
          const url = item.dataset.url;
          if (mode === 'image_group') {
            const block = addBlock({
              type: 'image_group',
              snapshot: { images: [{ url, filename: item.dataset.filename }], columns: 2 },
            });
          } else {
            const block = addBlock({
              type: 'image',
              snapshot: { url, filename: item.dataset.filename },
            });
          }
          modal.style.display = 'none';
        });
      });
    } catch (err) {
      grid.innerHTML = '<p>Failed to load images.</p>';
    }
  }

  function initGallery() {
    const modal = document.getElementById('imageGalleryModal');
    document.getElementById('galleryCloseBtn').addEventListener('click', () => {
      modal.style.display = 'none';
    });
    document.getElementById('galleryUploadBtn').addEventListener('click', () => {
      document.getElementById('galleryFileInput').click();
    });
    document.getElementById('galleryFileInput').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch('/quote_editor/upload-image', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          openGalleryModal('image');
        }
      } catch (err) {
        alert('Upload failed');
      }
    });
  }

  async function loadLayout() {
    const layoutId = document.getElementById('layoutSelector').value;
    if (!layoutId) return;
    try {
      const res = await fetch(`/quote_editor/layouts/${layoutId}`);
      const data = await res.json();
      if (data.success || data.layout) {
        blocks = [];
        document.getElementById('blocksContainer').innerHTML = '';
        const layout = data.layout || {};
        const blist = layout.blocks_json || [];
        blist.forEach(b => addBlock(b));
        initSortable();
      }
    } catch (err) {
      alert('Failed to load layout');
    }
  }

  async function saveCurrentLayout() {
    const name = prompt('Layout name:', 'My Layout');
    if (!name) return;
    const payload = {
      name,
      blocks_json: collectBlocks(),
      is_default: false,
    };
    try {
      const res = await fetch('/quote_editor/layouts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Layout saved');
        refreshLayoutSelector();
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  async function saveAsTemplate() {
    const name = prompt('Template name:', 'My Template');
    if (!name) return;
    const payload = {
      name,
      blocks_json: collectBlocks(),
      is_default: false,
    };
    try {
      const res = await fetch('/quote_editor/layouts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Template saved');
        refreshLayoutSelector();
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  function collectBlocks() {
    return blocks.map(b => ({
      ...b,
      snapshot: b.snapshot || {},
      editor_overrides: b.editor_overrides || {},
      flags: b.flags || {},
      settings: b.settings || {},
    }));
  }

  async function saveQuote() {
    const modal = document.getElementById('saveQuoteModal');
    modal.style.display = 'flex';
  }

  async function confirmSaveQuote() {
    const name = document.getElementById('quoteNameInput').value.trim();
    if (!name) return alert('Name is required');
    const payload = {
      name,
      client_name: document.getElementById('clientNameInput').value.trim(),
      notes: document.getElementById('quoteNotesInput').value.trim(),
      blocks_json: collectBlocks(),
      settings_json: {},
    };
    try {
      const res = await fetch('/quote_editor/save-quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Quote saved');
        document.getElementById('saveQuoteModal').style.display = 'none';
      } else {
        alert('Save failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  async function loadQuoteList() {
    const modal = document.getElementById('loadQuoteModal');
    modal.style.display = 'flex';
    const list = document.getElementById('loadQuoteList');
    list.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/quotes');
      const data = await res.json();
      const quotes = data.quotes || [];
      if (!quotes.length) {
        list.innerHTML = '<p>No saved quotes.</p>';
        return;
      }
      list.innerHTML = quotes.map(q => `
        <div class="quote-list-item">
          <div><strong>${escapeHtml(q.name)}</strong> <small>${escapeHtml(q.client_name || '')}</small></div>
          <div>
            <button data-load="${q.id}">Load</button>
            <button data-delete="${q.id}">Delete</button>
          </div>
        </div>
      `).join('');
      list.querySelectorAll('[data-load]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = parseInt(btn.dataset.load);
          const r = await fetch(`/quote_editor/load-quote/${id}`);
          const d = await r.json();
          if (d.success) {
            blocks = [];
            document.getElementById('blocksContainer').innerHTML = '';
            const quote = d.quote || {};
            const blist = quote.blocks_json || [];
            blist.forEach(b => addBlock(b));
            initSortable();
            modal.style.display = 'none';
          }
        });
      });
      list.querySelectorAll('[data-delete]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = parseInt(btn.dataset.delete);
          if (!confirm('Delete this quote?')) return;
          await fetch(`/quote_editor/quotes/${id}`, { method: 'DELETE' });
          loadQuoteList();
        });
      });
    } catch (err) {
      list.innerHTML = '<p>Failed to load quotes.</p>';
    }
  }

  function refreshLayoutSelector() {
    const sel = document.getElementById('layoutSelector');
    const current = sel.value;
    fetch('/quote_editor/layouts')
      .then(r => r.json())
      .then(data => {
        const layouts = data.layouts || [];
        sel.innerHTML = '<option value="">Select Layout...</option>' + layouts.map(l =>
          `<option value="${l.id}" ${current == l.id ? 'selected' : ''}>${escapeHtml(l.name)}${l.is_default ? ' (Default)' : ''}</option>`
        ).join('');
      });
  }

  function exportPDF() {
    window.location.href = '/api/quote-editor/export-pdf';
  }

  function exportDOCX() {
    window.location.href = '/api/quote-editor/export-docx';
  }

  function initInsertButtons() {
    document.querySelectorAll('.insert-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.blockType;
        if (type === 'image') {
          openGalleryModal('image');
          return;
        }
        if (type === 'image_group') {
          addBlock({ type: 'image_group', snapshot: { images: [], columns: 2 } });
          return;
        }
        if (type === 'calculator') {
          fetch('/quote_editor/add-calc-block')
            .then(r => r.json())
            .then(data => { if (data.success) addBlock(data.block); });
          return;
        }
        if (type === 'notes') {
          addBlock({ type: 'notes', snapshot: { content: '' } });
          return;
        }
      });
    });
  }

  function initActions() {
    document.getElementById('saveLayoutBtn').addEventListener('click', saveCurrentLayout);
    document.getElementById('saveAsTemplateBtn').addEventListener('click', saveAsTemplate);
    document.getElementById('saveQuoteBtn').addEventListener('click', saveQuote);
    document.getElementById('loadQuoteBtn').addEventListener('click', loadQuoteList);
    document.getElementById('exportPdfBtn').addEventListener('click', exportPDF);
    document.getElementById('exportDocxBtn').addEventListener('click', exportDOCX);
    document.getElementById('exportPdfBtn2').addEventListener('click', exportPDF);
    document.getElementById('exportDocxBtn2').addEventListener('click', exportDOCX);
    document.getElementById('loadLayoutBtn').addEventListener('click', loadLayout);
    document.getElementById('saveQuoteModal').querySelector('#closeSaveQuoteModal').addEventListener('click', () => {
      document.getElementById('saveQuoteModal').style.display = 'none';
    });
    document.getElementById('confirmSaveQuoteBtn').addEventListener('click', confirmSaveQuote);
    document.getElementById('closeLoadQuoteModal').addEventListener('click', () => {
      document.getElementById('loadQuoteModal').style.display = 'none';
    });
  }

  async function checkPendingBlocks() {
    const pending = sessionStorage.getItem('quote_editor_pending_block');
    if (pending) {
      try {
        const block = JSON.parse(pending);
        addBlock(block);
        sessionStorage.removeItem('quote_editor_pending_block');
      } catch (e) {
        console.error('Failed to parse pending block', e);
      }
    }
    const pendingList = sessionStorage.getItem('quote_editor_pending_blocks');
    if (pendingList) {
      try {
        const list = JSON.parse(pendingList);
        list.forEach(b => addBlock(b));
        sessionStorage.removeItem('quote_editor_pending_blocks');
      } catch (e) {
        console.error('Failed to parse pending blocks', e);
      }
    }
  }

  async function init() {
    refreshLayoutSelector();
    initSortable();
    initToolbar();
    initGallery();
    initInsertButtons();
    initActions();
    await checkPendingBlocks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

(function () {
  'use strict';

  const BLOCK_TYPES = {
    page_title: { label: 'Page Title', icon: 'H1' },
    category_title: { label: 'Category Title', icon: 'H2' },
    form_question: { label: 'Question', icon: '📋' },
    notes: { label: 'Notes', icon: '📝' },
    calculator: { label: 'Calculator', icon: '🧮' },
    image_group: { label: 'Image Group', icon: '🖼️' },
    image: { label: 'Image', icon: '🖼️' },
  };

  const PAGE_BREAK_AFTER = new Set(['page_title']);

  let blocks = [];
  let pages = [];
  let activeBlockId = null;
  let sortableInstance = null;
  let copiedSettings = null;

  function generateId() {
    return 'block_' + Math.random().toString(36).slice(2, 9);
  }

  function getBlockEl(blockId) {
    return document.querySelector(`.editor-block[data-block-id="${blockId}"]`);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getTypeInfo(type) {
    return BLOCK_TYPES[type] || { label: type, icon: '📄' };
  }

  function getDefaultSettings(type) {
    switch (type) {
      case 'page_title':
        return { margin_top: 10, margin_bottom: 10, padding: 12, alignment: 'left' };
      case 'category_title':
        return { margin_top: 5, margin_bottom: 5, padding: 12, alignment: 'left' };
      case 'form_question':
        return { margin_top: 2, margin_bottom: 2, padding: 12, alignment: 'left' };
      default:
        return { margin_top: 8, margin_bottom: 8, padding: 12, alignment: 'left' };
    }
  }

  function rebuildPages() {
    pages = [];
    let currentPage = [];
    blocks.forEach(block => {
      if (block.type === 'page_title' && currentPage.length > 0) {
        pages.push(currentPage);
        currentPage = [];
      }
      currentPage.push(block);
    });
    if (currentPage.length || pages.length === 0) {
      pages.push(currentPage);
    }
  }

  function renderCurrentPage() {
    const container = document.getElementById('blocksContainer');
    container.innerHTML = '';

    const pageIndex = Math.max(0, Math.min(window.__currentPageIndex || 0, pages.length - 1));
    window.__currentPageIndex = pageIndex;
    const pageBlocks = pages[pageIndex] || [];

    document.getElementById('currentPageNum').textContent = pageIndex + 1;
    document.getElementById('prevPageBtn').disabled = pageIndex === 0;
    document.getElementById('nextPageBtn').disabled = pageIndex >= pages.length - 1;

    if (!pageBlocks.length) {
      container.innerHTML = '<p class="editor-canvas__empty">This page is empty. Add blocks from the right panel.</p>';
      return;
    }

    pageBlocks.forEach(block => {
      const el = createBlockEl(block);
      container.appendChild(el);
      applyBlockStyles(block);
    });

    if (sortableInstance) {
      sortableInstance.destroy();
      sortableInstance = null;
    }

    const canvas = document.getElementById('blocksContainer');
    sortableInstance = Sortable.create(canvas, {
      animation: 150,
      handle: '.editor-block__drag-handle',
      onEnd: (evt) => {
        const newOrder = [...canvas.querySelectorAll('.editor-block')].map(el => el.dataset.blockId);
        const pageBlockIds = pageBlocks.map(b => b.id);
        const remainingBlocks = blocks.filter(b => !pageBlockIds.includes(b.id));

        const reordered = newOrder.map(id => pageBlocks.find(b => b.id === id)).filter(Boolean);
        blocks = [...remainingBlocks, ...reordered];
        rebuildPages();
      }
    });
  }

  function createBlockEl(block) {
    const wrapper = document.createElement('div');
    wrapper.className = 'editor-block';
    wrapper.dataset.blockId = block.id;
    wrapper.dataset.blockType = block.type;

    const typeInfo = getTypeInfo(block.type);
    const snapshot = block.snapshot || {};
    const flags = block.flags || {};

    let contentHtml = '';
    let isEditable = 'true';

    if (block.type === 'page_title') {
      contentHtml = `<h1>${escapeHtml(snapshot.title || '')}</h1>`;
      isEditable = 'false';
    } else if (block.type === 'category_title') {
      contentHtml = `<h2>${escapeHtml(snapshot.title || '')}</h2>`;
      isEditable = 'false';
    } else if (block.type === 'form_question') {
      const label = escapeHtml(snapshot.label || '');
      const value = escapeHtml(snapshot.value || '');
      contentHtml = label ? `<strong>${label}:</strong> ${value}` : value;
    } else {
      contentHtml = renderBlockContent(block);
    }

    wrapper.innerHTML = `
      <div class="editor-block__header">
        <span class="editor-block__drag-handle" title="Drag to reorder">☰</span>
        <span class="editor-block__type-label">${typeInfo.icon} ${typeInfo.label}</span>
        <span class="editor-block__source-dot ${flags.source_dirty ? 'editor-block__source-dot--dirty' : ''} ${flags.editor_dirty ? 'editor-block__source-dot--editor' : ''}" title=""></span>
        <button class="editor-block__remove" title="Remove block">&times;</button>
      </div>
      <div class="editor-block__content" contenteditable="${isEditable}" data-placeholder="Type here...">
        ${contentHtml}
      </div>
    `;

    wrapper.querySelector('.editor-block__remove').addEventListener('click', () => {
      removeBlock(block.id);
    });

    const contentEl = wrapper.querySelector('.editor-block__content');
    if (isEditable === 'true') {
      contentEl.addEventListener('input', () => {
        block.editor_overrides = { ...(block.editor_overrides || {}), content: contentEl.innerHTML };
        block.flags = block.flags || {};
        block.flags.editor_dirty = true;
        wrapper.querySelector('.editor-block__source-dot').classList.add('editor-block__source-dot--editor');
      });
    }

    wrapper.addEventListener('click', (e) => {
      if (e.target.closest('.editor-block__header')) return;
      setActiveBlock(block.id);
    });

    return wrapper;
  }

  function renderBlockContent(block) {
    const snapshot = block.snapshot || {};
    switch (block.type) {
      case 'notes':
        return snapshot.content || '<p>Start typing notes...</p>';
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

  function updateSettingsPanel() {
    const panel = document.getElementById('settingsPanel');
    if (!activeBlockId) {
      panel.innerHTML = '<p class="editor-settings-placeholder">Select a block to edit its settings.</p>';
      return;
    }
    const block = blocks.find(b => b.id === activeBlockId);
    if (!block) {
      panel.innerHTML = '<p class="editor-settings-placeholder">Select a block to edit its settings.</p>';
      return;
    }

    const settings = block.settings || getDefaultSettings(block.type);
    const typeInfo = getTypeInfo(block.type);

    let html = `
      <div class="settings-block">
        <div class="settings-block__header">
          <span>${typeInfo.icon} ${typeInfo.label}</span>
        </div>
        <div class="settings-block__body">
          <label>Margin Top
            <input type="number" data-setting="margin_top" value="${settings.margin_top || 8}" min="0" max="40">
          </label>
          <label>Margin Bottom
            <input type="number" data-setting="margin_bottom" value="${settings.margin_bottom || 8}" min="0" max="40">
          </label>
          <label>Padding
            <input type="number" data-setting="padding" value="${settings.padding || 12}" min="0" max="40">
          </label>
          <label>Alignment
            <select data-setting="alignment">
              <option value="left" ${settings.alignment === 'left' ? 'selected' : ''}>Left</option>
              <option value="center" ${settings.alignment === 'center' ? 'selected' : ''}>Center</option>
              <option value="right" ${settings.alignment === 'right' ? 'selected' : ''}>Right</option>
            </select>
          </label>
        </div>
      </div>
    `;

    if (block.type === 'page_title' || block.type === 'category_title') {
      const title = escapeHtml(block.snapshot?.title || '');
      html += `
        <div class="settings-block">
          <div class="settings-block__header">Content</div>
          <div class="settings-block__body">
            <label>Title Text
              <input type="text" data-setting="title" value="${title}">
            </label>
          </div>
        </div>
      `;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('[data-setting]').forEach(input => {
      input.addEventListener('input', () => {
        const key = input.dataset.setting;
        if (key === 'title') {
          block.snapshot = block.snapshot || {};
          block.snapshot.title = input.value;
          const contentEl = getBlockEl(block.id)?.querySelector('.editor-block__content');
          if (contentEl && block.type === 'page_title') {
            contentEl.innerHTML = `<h1>${escapeHtml(input.value)}</h1>`;
          } else if (contentEl && block.type === 'category_title') {
            contentEl.innerHTML = `<h2>${escapeHtml(input.value)}</h2>`;
          }
          return;
        }
        block.settings = block.settings || {};
        block.settings[key] = input.type === 'number' ? parseInt(input.value, 10) || 0 : input.value;
        applyBlockStyles(block);
      });
    });
  }

  function applyBlockStyles(block) {
    const el = getBlockEl(block.id);
    if (!el) return;
    const s = block.settings || {};
    const content = el.querySelector('.editor-block__content');
    if (content) {
      content.style.marginTop = (s.margin_top || 0) + 'px';
      content.style.marginBottom = (s.margin_bottom || 0) + 'px';
      content.style.padding = (s.padding || 0) + 'px';
      content.style.textAlign = s.alignment || 'left';
    }
  }

  function addBlock(blockData) {
    const block = {
      id: blockData.id || generateId(),
      type: blockData.type,
      snapshot: blockData.snapshot || {},
      editor_overrides: blockData.editor_overrides || {},
      flags: blockData.flags || { source_dirty: false, editor_dirty: false },
      settings: blockData.settings || getDefaultSettings(blockData.type),
    };
    blocks.push(block);
    rebuildPages();
    window.__currentPageIndex = pages.length - 1;
    renderCurrentPage();
    setActiveBlock(block.id);
    return block;
  }

  function removeBlock(blockId) {
    blocks = blocks.filter(b => b.id !== blockId);
    rebuildPages();
    const wasActive = activeBlockId === blockId;
    if (wasActive) {
      activeBlockId = null;
      updateSettingsPanel();
    }
    renderCurrentPage();
  }

  function setActiveBlock(blockId) {
    activeBlockId = blockId;
    document.querySelectorAll('.editor-block').forEach(el => el.style.outline = '');
    const el = getBlockEl(blockId);
    if (el) {
      el.style.outline = '2px solid #0d6efd';
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    updateSettingsPanel();
  }

  function initToolbar() {
    const toolbar = document.getElementById('editorToolbar');
    const textSelect = document.getElementById('textTypeSelect');

    toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-command]');
      if (!btn) return;
      const command = btn.dataset.command;
      document.execCommand(command, false, null);
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

    textSelect.addEventListener('change', () => {
      const value = textSelect.value;
      const active = document.querySelector('.editor-block__content:focus');
      if (!active) return;
      if (value === 'NOTE' || value === 'GUIDE') {
        document.execCommand('formatBlock', false, 'DIV');
        active.classList.add(`editor-block__${value.toLowerCase()}`);
      } else {
        document.execCommand('formatBlock', false, value);
      }
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
    });

    document.getElementById('insertUnorderedList').addEventListener('click', () => {
      document.execCommand('insertUnorderedList', false, null);
    });

    document.getElementById('insertOrderedList').addEventListener('click', () => {
      document.execCommand('insertOrderedList', false, null);
    });

    document.getElementById('insertImageToolbarBtn').addEventListener('click', () => {
      openGalleryModal('image');
    });
  }

  function initPageNav() {
    document.getElementById('prevPageBtn').addEventListener('click', () => {
      const current = window.__currentPageIndex || 0;
      if (current > 0) {
        window.__currentPageIndex = current - 1;
        activeBlockId = null;
        updateSettingsPanel();
        renderCurrentPage();
      }
    });

    document.getElementById('nextPageBtn').addEventListener('click', () => {
      const current = window.__currentPageIndex || 0;
      if (current < pages.length - 1) {
        window.__currentPageIndex = current + 1;
        activeBlockId = null;
        updateSettingsPanel();
        renderCurrentPage();
      }
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
            addBlock({
              type: 'image_group',
              snapshot: { images: [{ url, filename: item.dataset.filename }], columns: 2 },
            });
          } else {
            addBlock({
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
      if (data.layout) {
        blocks = [];
        activeBlockId = null;
        updateSettingsPanel();
        const layout = data.layout || {};
        const blist = layout.blocks_json || [];
        blist.forEach(b => addBlock(b));
      }
    } catch (err) {
      alert('Failed to load layout');
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

  function openSaveModal() {
    document.getElementById('saveModal').style.display = 'flex';
  }

  async function confirmSave() {
    const name = document.getElementById('saveNameInput').value.trim();
    if (!name) return alert('Name is required');
    const asTemplate = document.getElementById('saveAsTemplateCheckbox').checked;
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
        alert(asTemplate ? 'Template saved' : 'Quote saved');
        document.getElementById('saveModal').style.display = 'none';
        refreshLayoutSelector();
      } else {
        alert('Save failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  function openLoadModal() {
    document.getElementById('loadModal').style.display = 'flex';
    loadQuotesList();
    loadTemplatesList();
  }

  async function loadQuotesList() {
    const container = document.getElementById('loadQuotesList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/quotes');
      const data = await res.json();
      const quotes = data.quotes || [];
      if (!quotes.length) {
        container.innerHTML = '<p>No saved quotes.</p>';
        return;
      }
      container.innerHTML = quotes.map(q => `
        <div class="quote-list-item">
          <div><strong>${escapeHtml(q.name)}</strong> <small>${escapeHtml(q.client_name || '')}</small></div>
          <div>
            <button data-load="${q.id}">Load</button>
            <button class="delete" data-delete="${q.id}">Delete</button>
          </div>
        </div>
      `).join('');
      container.querySelectorAll('[data-load]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = parseInt(btn.dataset.load);
          const r = await fetch(`/quote_editor/load-quote/${id}`);
          const d = await r.json();
          if (d.success) {
            blocks = [];
            activeBlockId = null;
            updateSettingsPanel();
            const quote = d.quote || {};
            const blist = quote.blocks_json || [];
            blist.forEach(b => addBlock(b));
            document.getElementById('loadModal').style.display = 'none';
          }
        });
      });
      container.querySelectorAll('[data-delete]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = parseInt(btn.dataset.delete);
          if (!confirm('Delete this quote?')) return;
          await fetch(`/quote_editor/quotes/${id}`, { method: 'DELETE' });
          loadQuotesList();
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load quotes.</p>';
    }
  }

  async function loadTemplatesList() {
    const container = document.getElementById('loadTemplatesList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/layouts');
      const data = await res.json();
      const layouts = data.layouts || [];
      if (!layouts.length) {
        container.innerHTML = '<p>No templates available.</p>';
        return;
      }
      container.innerHTML = layouts.map(l => `
        <div class="quote-list-item">
          <div><strong>${escapeHtml(l.name)}</strong> ${l.is_default ? '(Default)' : ''}</div>
          <div><button data-load-template="${l.id}">Load</button></div>
        </div>
      `).join('');
      container.querySelectorAll('[data-load-template]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = parseInt(btn.dataset.loadTemplate);
          const r = await fetch(`/quote_editor/layouts/${id}`);
          const d = await r.json();
          if (d.layout) {
            blocks = [];
            activeBlockId = null;
            updateSettingsPanel();
            const layout = d.layout || {};
            const blist = layout.blocks_json || [];
            blist.forEach(b => addBlock(b));
            document.getElementById('loadModal').style.display = 'none';
          }
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load templates.</p>';
    }
  }

  function openExportModal() {
    document.getElementById('exportModal').style.display = 'flex';
  }

  function exportPDF() {
    window.location.href = '/api/quote-editor/export-pdf';
    document.getElementById('exportModal').style.display = 'none';
  }

  function exportDOCX() {
    window.location.href = '/api/quote-editor/export-docx';
    document.getElementById('exportModal').style.display = 'none';
  }

  let previewPageIndex = 0;

  function openPreviewModal() {
    previewPageIndex = Math.max(0, Math.min(window.__currentPageIndex || 0, pages.length - 1));
    renderPreviewPage();
    document.getElementById('previewModal').style.display = 'flex';
  }

  function closePreviewModal() {
    document.getElementById('previewModal').style.display = 'none';
  }

  function renderPreviewPage() {
    const pageBlocks = pages[previewPageIndex] || [];
    document.getElementById('previewPageNum').textContent = previewPageIndex + 1;
    document.getElementById('previewPrevBtn').disabled = previewPageIndex === 0;
    document.getElementById('previewNextBtn').disabled = previewPageIndex >= pages.length - 1;

    let html = '';
    pageBlocks.forEach(block => {
      const snapshot = block.snapshot || {};
      const settings = block.settings || {};
      const marginTop = settings.margin_top || 8;
      const marginBottom = settings.margin_bottom || 8;
      const padding = settings.padding || 12;
      const alignment = settings.alignment || 'left';

      if (block.type === 'page_title') {
        html += `<h1 style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};">${escapeHtml(snapshot.title || '')}</h1>`;
      } else if (block.type === 'category_title') {
        html += `<h2 style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};">${escapeHtml(snapshot.title || '')}</h2>`;
      } else if (block.type === 'form_question') {
        const label = escapeHtml(snapshot.label || '');
        const value = escapeHtml(snapshot.value || '');
        html += `<div class="preview-question" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};"><strong>${label}:</strong> ${value}</div>`;
      } else if (block.type === 'calculator') {
        const groups = snapshot.groups || [];
        if (groups.length) {
          html += `<div class="preview-calculator" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px;"><table class="calc-table"><thead><tr><th>Item</th><th>Total</th><th>Group</th></tr></thead><tbody>`;
          groups.forEach(g => {
            (g.items || []).forEach(item => {
              html += `<tr><td>${escapeHtml(item.output_title || '')}</td><td>${item.line_total?.toFixed(2) || '0.00'}</td><td>${escapeHtml(g.name || '')}</td></tr>`;
            });
          });
          html += `</tbody></table><p><strong>Grand Total: ${snapshot.grand_total?.toFixed(2) || '0.00'}</strong></p></div>`;
        }
      } else if (block.type === 'notes') {
        html += `<div class="preview-notes" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px;">${snapshot.content || ''}</div>`;
      } else if (block.type === 'image') {
        const url = snapshot.url || '';
        if (url) {
          html += `<div class="preview-image" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};"><img src="${escapeHtml(url)}" style="max-width:100%; height:auto;" /></div>`;
        }
      } else if (block.type === 'image_group') {
        const images = snapshot.images || [];
        const cols = snapshot.columns || 2;
        if (images.length) {
          html += `<div class="preview-image-group" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; display:grid; grid-template-columns: repeat(${cols}, 1fr); gap:8px;">`;
          images.forEach(img => {
            html += `<img src="${escapeHtml(img.url || '')}" style="width:100%; height:auto;" />`;
          });
          html += `</div>`;
        }
      }
    });

    document.getElementById('previewPage').innerHTML = html || '<p style="text-align:center; color:#999; padding:40px;">This page is empty.</p>';
  }

  function initPreviewNav() {
    document.getElementById('previewPrevBtn').addEventListener('click', () => {
      if (previewPageIndex > 0) {
        previewPageIndex--;
        renderPreviewPage();
      }
    });

    document.getElementById('previewNextBtn').addEventListener('click', () => {
      if (previewPageIndex < pages.length - 1) {
        previewPageIndex++;
        renderPreviewPage();
      }
    });
  }

  function initModals() {
    document.getElementById('previewBtn').addEventListener('click', openPreviewModal);
    document.getElementById('saveBtn').addEventListener('click', openSaveModal);
    document.getElementById('loadBtn').addEventListener('click', openLoadModal);
    document.getElementById('exportBtn').addEventListener('click', openExportModal);
    document.getElementById('closeSaveModal').addEventListener('click', () => {
      document.getElementById('saveModal').style.display = 'none';
    });
    document.getElementById('confirmSaveBtn').addEventListener('click', confirmSave);
    document.getElementById('closeLoadModal').addEventListener('click', () => {
      document.getElementById('loadModal').style.display = 'none';
    });
    document.getElementById('closeExportModal').addEventListener('click', () => {
      document.getElementById('exportModal').style.display = 'none';
    });
    document.getElementById('exportPdfBtn').addEventListener('click', exportPDF);
    document.getElementById('exportDocxBtn').addEventListener('click', exportDOCX);
    document.getElementById('closePreviewModal').addEventListener('click', closePreviewModal);

    document.querySelectorAll('#loadTabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#loadTabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.getElementById('loadQuotesList').style.display = tab === 'quotes' ? 'block' : 'none';
        document.getElementById('loadTemplatesList').style.display = tab === 'templates' ? 'block' : 'none';
      });
    });
  }

  function initOutsideClickClose() {
    document.querySelectorAll('.modal').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.style.display = 'none';
        }
      });
    });
  }

  function initContextMenu() {
    const existingMenu = document.getElementById('blockContextMenu');
    if (existingMenu) existingMenu.remove();

    const menu = document.createElement('div');
    menu.id = 'blockContextMenu';
    menu.className = 'block-context-menu';
    menu.innerHTML = `
      <div class="context-menu-item" data-action="copy-style">Copy Style</div>
      <div class="context-menu-item" data-action="paste-style">Paste Style</div>
    `;
    document.body.appendChild(menu);

    document.addEventListener('click', () => {
      menu.style.display = 'none';
    });

    document.addEventListener('contextmenu', (e) => {
      const blockEl = e.target.closest('.editor-block');
      if (!blockEl) {
        menu.style.display = 'none';
        return;
      }

      e.preventDefault();
      const blockId = blockEl.dataset.blockId;
      const block = blocks.find(b => b.id === blockId);
      if (!block) return;

      activeBlockId = blockId;
      setActiveBlock(blockId);

      menu.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', () => {
          const action = item.dataset.action;
          if (action === 'copy-style') {
            copiedSettings = {
              settings: { ...(block.settings || {}) },
              content: getBlockEl(blockId)?.querySelector('.editor-block__content')?.innerHTML || '',
            };
            menu.style.display = 'none';
          } else if (action === 'paste-style') {
            if (copiedSettings && activeBlockId) {
              const targetBlock = blocks.find(b => b.id === activeBlockId);
              if (targetBlock) {
                targetBlock.settings = { ...copiedSettings.settings };
                applyBlockStyles(targetBlock);
                const targetContent = getBlockEl(activeBlockId)?.querySelector('.editor-block__content');
                if (targetContent && copiedSettings.content) {
                  targetContent.innerHTML = copiedSettings.content;
                  targetBlock.editor_overrides = { ...(targetBlock.editor_overrides || {}), content: copiedSettings.content };
                  targetBlock.flags = targetBlock.flags || {};
                  targetBlock.flags.editor_dirty = true;
                  targetBlock.querySelector('.editor-block__source-dot')?.classList.add('editor-block__source-dot--editor');
                }
                updateSettingsPanel();
              }
            }
            menu.style.display = 'none';
          }
        });
      });

      menu.style.display = 'block';
      menu.style.left = e.clientX + 'px';
      menu.style.top = e.clientY + 'px';
    });
  }

  async function checkPendingBlocks() {
    if (window.__quoteEditorPendingBlock) {
      try {
        addBlock(window.__quoteEditorPendingBlock);
        window.__quoteEditorPendingBlock = null;
      } catch (e) {
        console.error('Failed to parse pending block', e);
      }
    }
    if (window.__quoteEditorPendingBlocks && Array.isArray(window.__quoteEditorPendingBlocks)) {
      try {
        window.__quoteEditorPendingBlocks.forEach(b => addBlock(b));
        window.__quoteEditorPendingBlocks = [];
      } catch (e) {
        console.error('Failed to parse pending blocks', e);
      }
    }
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
        addBlock({ type });
      });
    });
  }

  function refreshLayoutSelector() {
    const sel = document.getElementById('layoutSelector');
    if (!sel) return;
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

  async function init() {
    refreshLayoutSelector();
    initToolbar();
    initPageNav();
    initPreviewNav();
    initGallery();
    initInsertButtons();
    initModals();
    initOutsideClickClose();
    initContextMenu();
    updateSettingsPanel();
    await checkPendingBlocks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

(function () {
  'use strict';

  const BLOCK_TYPES = {
    page_title: { label: 'Page Title', icon: '' },
    page_heading: { label: 'Page Heading', icon: '' },
    category_title: { label: 'Category Title', icon: 'H2' },
    form_question: { label: 'Question', icon: '📋' },
    notes: { label: 'Notes', icon: '📝' },
    calculator: { label: 'Calculator', icon: '🧮' },
    image_group: { label: 'Image Group', icon: '🖼️' },
    image: { label: 'Image', icon: '🖼️' },
    page_break: { label: 'Page Break', icon: '↵' },
  };

let blocks = [];
let pages = [];
let activeBlockId = null;
let selectedBlockIds = new Set();
let lastClickedBlockId = null;
let sortableInstance = null;
let listGroupCounter = 0;
let copiedSettings = null;
let currentQuoteId = null;
let documentStyles = {
  font_family: 'Arial, sans-serif',
  font_size_base: 16,
  header_font_size: 10,
  footer_font_size: 8,
  page_size: 'A4',
  margins: {
    margin_top: 20,
    margin_bottom: 20,
    margin_left: 25,
    margin_right: 25,
  },
  header: {
    enabled: true,
    document_id_type: 'quote_number',
    document_id_manual: '',
    logo_url: '',
    logo_width: 120,
    logo_height: 40,
    logo_alignment: 'center',
    doc_id_alignment: 'center',
    divider_style: 'single',
    divider_thickness: 1,
    margin_top: 0,
    margin_bottom: 0,
    margin_left: 0,
    margin_right: 0,
    hide_on_cover: false,
  },
  footer: {
    enabled: true,
    divider_style: 'single',
    divider_thickness: 1,
    page_number_mode: 'on',
    page_number_alignment: 'center',
    margin_top: 10,
    margin_left: 0,
    margin_right: 0,
    margin_bottom: 10,
    hide_on_cover: false,
  },
  typography: {
    h1: { family: '', weight: '', size: 24, bold: false, italic: false, underline: false, color: '' },
    h2: { family: '', weight: '', size: 20, bold: false, italic: false, underline: false, color: '' },
    h3: { family: '', weight: '', size: 18, bold: false, italic: false, underline: false, color: '' },
    para: { family: '', weight: '', size: 16, bold: false, italic: false, underline: false, color: '' },
    notes: { family: '', weight: '', size: 14, bold: false, italic: false, underline: false, color: '' },
    guide: { family: '', weight: '', size: 14, bold: false, italic: false, underline: false, color: '' },
    guidance: { family: '', weight: '', size: 14, bold: false, italic: false, underline: false, color: '' },
  },
  tables: {
    border: '1px solid #ccc',
    header_bg: '#f5f5f5',
    row_bg: '#ffffff',
    alt_row_bg: '#fafafa',
    font_size: 14,
  },
  images: {
    frame: 'none',
    shadow: false,
  },
  links: {
    color: '#0d6efd',
    underline: true,
  },
};

const TYPO_ELEMENTS = ['h1', 'h2', 'h3', 'para', 'notes', 'guide', 'guidance'];
const TYPO_LABELS = {
  h1: 'Page Title', h2: 'Category Title', h3: 'Heading 3',
  para: 'Paragraph', notes: 'Notes', guide: 'Guide', guidance: 'Guidance',
};
const FONT_FAMILIES = [
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: 'Helvetica, sans-serif', label: 'Helvetica' },
  { value: 'Times New Roman, serif', label: 'Times New Roman' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Courier New, monospace', label: 'Courier New' },
  { value: 'Verdana, sans-serif', label: 'Verdana' },
  { value: 'Roboto, sans-serif', label: 'Roboto (Google)' },
  { value: 'Open Sans, sans-serif', label: 'Open Sans (Google)' },
  { value: 'Lora, serif', label: 'Lora (Google)' },
  { value: 'Merriweather, serif', label: 'Merriweather (Google)' },
  { value: 'Montserrat, sans-serif', label: 'Montserrat (Google)' },
  { value: 'Poppins, sans-serif', label: 'Poppins (Google)' },
];
const FONT_WEIGHTS = [
  { value: '300', label: 'Light (300)' },
  { value: '400', label: 'Regular (400)' },
  { value: '500', label: 'Medium (500)' },
  { value: '600', label: 'Semibold (600)' },
  { value: '700', label: 'Bold (700)' },
  { value: 'bold', label: 'Bold' },
];
const IMAGE_FRAMES = [
  { value: 'none', label: 'None' },
  { value: '1px solid #ccc', label: 'Thin border' },
  { value: '3px solid #333', label: 'Thick border' },
  { value: '6px double #999', label: 'Double border' },
];

  let historyStack = [];
  let historyIndex = -1;
  const MAX_HISTORY = 50;

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
        return { margin_top: 0, margin_bottom: 0, padding: 0, alignment: 'left', font_size: 16, hidden: false };
      case 'page_heading':
        return { margin_top: 10, margin_bottom: 10, padding: 12, alignment: 'left', font_size: 24 };
      case 'category_title':
        return { margin_top: 5, margin_bottom: 5, padding: 12, alignment: 'left', font_size: 20 };
      case 'form_question':
        return { margin_top: 2, margin_bottom: 2, padding: 12, alignment: 'left', font_size: 16 };
      default:
        return { margin_top: 8, margin_bottom: 8, padding: 12, alignment: 'left', font_size: 16 };
    }
  }

  function pushHistory() {
    const state = JSON.stringify(blocks);
    if (historyIndex >= 0 && historyStack[historyIndex] === state) return;
    historyStack = historyStack.slice(0, historyIndex + 1);
    historyStack.push(state);
    if (historyStack.length > MAX_HISTORY) historyStack.shift();
    historyIndex = historyStack.length - 1;
  }

  function undo() {
    if (historyIndex <= 0) return;
    historyIndex--;
    blocks = JSON.parse(historyStack[historyIndex]);
    rebuildPages();
    renderCurrentPage();
    updateNavPanel();
  }

  function redo() {
    if (historyIndex >= historyStack.length - 1) return;
    historyIndex++;
    blocks = JSON.parse(historyStack[historyIndex]);
    rebuildPages();
    renderCurrentPage();
    updateNavPanel();
  }

  function rebuildPages() {
    pages = [];
    let currentPage = [];
    blocks.forEach(block => {
      if ((block.type === 'page_title' || block.type === 'page_break') && currentPage.length > 0) {
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

    let pageIndex = Math.max(0, Math.min(window.__currentPageIndex || 0, pages.length - 1));
    window.__currentPageIndex = pageIndex;
    let pageBlocks = pages[pageIndex] || [];

    if (pageBlocks.length) {
      const separator = pageBlocks.find(b => b.type === 'page_title' || b.type === 'page_break');
      if (separator && separator.flags && separator.flags.hidden) {
        let nextIndex = pageIndex + 1;
        while (nextIndex < pages.length) {
          const nextPage = pages[nextIndex] || [];
          const nextSep = nextPage.find(b => b.type === 'page_title' || b.type === 'page_break');
          if (nextSep && nextSep.flags && nextSep.hidden) {
            nextIndex++;
          } else {
            break;
          }
        }
        if (nextIndex >= pages.length) {
          nextIndex = 0;
          while (nextIndex < pageIndex) {
            const prevPage = pages[nextIndex] || [];
            const prevSep = prevPage.find(b => b.type === 'page_title' || b.type === 'page_break');
            if (prevSep && prevSep.flags && prevSep.flags.hidden) {
              nextIndex++;
            } else {
              break;
            }
          }
        }
        pageIndex = nextIndex;
        window.__currentPageIndex = pageIndex;
        pageBlocks = pages[pageIndex] || [];
      }
    }

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

    wrapListGroups(container, pageBlocks);

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
        pushHistory();
        rebuildPages();
        updateNavPanel();
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
      contentHtml = '';
      isEditable = 'false';
      if (flags.hidden) {
        wrapper.style.display = 'none';
      }
    } else if (block.type === 'page_heading') {
      contentHtml = `<h1>${escapeHtml(snapshot.title || '')}</h1>`;
      isEditable = 'true';
    } else if (block.type === 'category_title') {
      const catImg = snapshot.category_image
        ? `<img src="${escapeHtml(snapshot.category_image)}" alt="" class="category-image" style="max-width:200px;max-height:120px;display:block;margin-bottom:8px;border-radius:4px;">`
        : '';
      contentHtml = `${catImg}<h2>${escapeHtml(snapshot.title || '')}</h2>`;
      isEditable = 'false';
    } else if (block.type === 'page_break') {
      contentHtml = '<div class="page-break-visual">Page Break</div>';
      isEditable = 'false';
    } else if (block.type === 'form_question') {
      const label = escapeHtml(snapshot.label || '');
      const value = escapeHtml(snapshot.value || '');
      const guidance = escapeHtml(snapshot.output_guidance || '');
      contentHtml = label ? `<strong>${label}:</strong> ${value}` : value;
      contentHtml += guidance ? `<div class="preview-guidance"${previewMergedStyle('guidance', '')}>${guidance}</div>` : '';
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
      pushHistory();
      removeBlock(block.id);
    });

    const contentEl = wrapper.querySelector('.editor-block__content');
    if (isEditable === 'true') {
      contentEl.addEventListener('input', () => {
        pushHistory();
        block.editor_overrides = { ...(block.editor_overrides || {}), content: contentEl.innerHTML };
        block.flags = block.flags || {};
        block.flags.editor_dirty = true;
        wrapper.querySelector('.editor-block__source-dot').classList.add('editor-block__source-dot--editor');
      });
    }

    wrapper.addEventListener('click', (e) => {
      if (e.target.closest('.editor-block__header')) return;
      if (e.shiftKey && lastClickedBlockId) {
        e.preventDefault();
        selectBlockRange(lastClickedBlockId, block.id);
      } else if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        toggleBlockSelection(block.id);
      } else {
        setActiveBlock(block.id);
      }
      lastClickedBlockId = block.id;
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

  function applyBlockStyles(block) {
    const el = getBlockEl(block.id);
    if (!el) return;
    const s = block.settings || {};
    const content = el.querySelector('.editor-block__content');
    const inList = !!block.list_group_id;
    if (content) {
      content.style.marginTop = inList ? '0px' : ((s.margin_top || 0) + 'px');
      content.style.marginBottom = inList ? '0px' : ((s.margin_bottom || 0) + 'px');
      if (inList) {
        content.style.padding = '0px';
        content.style.paddingLeft = '24px';
      } else {
        content.style.padding = (s.padding || 0) + 'px';
      }
      content.style.textAlign = s.alignment || 'left';
      content.style.fontSize = (s.font_size || 16) + 'px';
    }
    if (inList && el) {
      el.style.marginTop = '0px';
      el.style.marginBottom = '0px';
      el.style.paddingTop = '0px';
      el.style.paddingBottom = '0px';
    }
  }

  function addBlock(blockData) {
    pushHistory();
    const block = {
      id: blockData.id || generateId(),
      type: blockData.type,
      source_page: blockData.source_page || '',
      source_block_id: blockData.source_block_id || '',
      list_group_id: blockData.list_group_id || null,
      list_type: blockData.list_type || 'ul',
      list_index: blockData.list_index || 0,
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
    updateNavPanel();
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
    updateNavPanel();
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
    updateNavHighlight();
  }

  function toggleBlockSelection(blockId) {
    if (selectedBlockIds.has(blockId)) {
      selectedBlockIds.delete(blockId);
    } else {
      selectedBlockIds.add(blockId);
    }
    updateSelectionUI();
  }

  function selectBlockRange(startId, endId) {
    if (!startId || !endId || startId === endId) {
      if (startId) selectedBlockIds.add(startId);
      updateSelectionUI();
      return;
    }
    const startIndex = blocks.findIndex(b => b.id === startId);
    const endIndex = blocks.findIndex(b => b.id === endId);
    if (startIndex === -1 || endIndex === -1) {
      if (startId) selectedBlockIds.add(startId);
      updateSelectionUI();
      return;
    }
    const [from, to] = startIndex < endIndex ? [startIndex, endIndex] : [endIndex, startIndex];
    for (let i = from; i <= to; i++) {
      selectedBlockIds.add(blocks[i].id);
    }
    updateSelectionUI();
  }

  function clearSelection() {
    selectedBlockIds.clear();
    updateSelectionUI();
  }

  function updateSelectionUI() {
    document.querySelectorAll('.editor-block').forEach(el => {
      const id = el.dataset.blockId;
      if (selectedBlockIds.has(id)) {
        el.style.outline = '2px solid #0d6efd';
      } else if (id !== activeBlockId) {
        el.style.outline = '';
      }
    });
  }

  function getSelectedBlocks() {
    if (selectedBlockIds.size > 0) {
      return blocks.filter(b => selectedBlockIds.has(b.id));
    }
    const active = blocks.find(b => b.id === activeBlockId);
    return active ? [active] : [];
  }

  function applyListToSelection(listType) {
    const selected = getSelectedBlocks();
    if (!selected.length) return;
    listGroupCounter += 1;
    const groupId = 'list_' + listGroupCounter;
    selected.forEach((block, index) => {
      block.list_group_id = groupId;
      block.list_type = listType;
      block.list_index = index;
    });
    pushHistory();
    rebuildPages();
    renderCurrentPage();
    updateNavPanel();
    clearSelection();
  }

  function clearListFromSelection() {
    const selected = getSelectedBlocks();
    if (!selected.length) return;
    selected.forEach(block => {
      delete block.list_group_id;
      delete block.list_type;
      delete block.list_index;
    });
    pushHistory();
    rebuildPages();
    renderCurrentPage();
    updateNavPanel();
    clearSelection();
  }

  function clearAllLists() {
    blocks.forEach(block => {
      delete block.list_group_id;
      delete block.list_type;
      delete block.list_index;
    });
    pushHistory();
    rebuildPages();
    renderCurrentPage();
    updateNavPanel();
    clearSelection();
  }

  function wrapListGroups(container, pageBlocks) {
    const groups = new Map();
    pageBlocks.forEach(block => {
      const gid = block.list_group_id;
      if (!gid) return;
      if (!groups.has(gid)) groups.set(gid, []);
      groups.get(gid).push(block);
    });

    if (!groups.size) return;

    const blockElMap = new Map();
    container.querySelectorAll('.editor-block').forEach(el => {
      blockElMap.set(el.dataset.blockId, el);
    });

    const groupEntries = Array.from(groups.entries()).sort((a, b) => {
      const aIdx = pageBlocks.findIndex(bl => bl.id === a[1][0].id);
      const bIdx = pageBlocks.findIndex(bl => bl.id === b[1][0].id);
      return bIdx - aIdx;
    });

    groupEntries.forEach(([gid, groupBlocks]) => {
      const listType = groupBlocks[0].list_type || 'ul';
      const listEl = document.createElement(listType);
      listEl.className = 'editor-list-group';

      const firstBlock = groupBlocks[0];
      const firstEl = blockElMap.get(firstBlock.id);
      if (!firstEl || firstEl.parentNode !== container) return;

      const insertIndex = Array.from(container.children).indexOf(firstEl);

      groupBlocks.forEach((block, idx) => {
        const blockEl = blockElMap.get(block.id);
        if (!blockEl) return;
        const li = document.createElement('li');
        li.appendChild(blockEl);
        blockEl.classList.add('editor-block--in-list');
        blockEl.setAttribute('data-list-type', listType);
        blockEl.setAttribute('data-list-index', String(idx + 1));
        const contentEl = blockEl.querySelector('.editor-block__content');
        if (contentEl) {
          contentEl.setAttribute('data-list-index', String(idx + 1));
        }
        listEl.appendChild(li);
      });

      if (!listEl.children.length) return;

      listEl.querySelectorAll('.editor-block').forEach(blockEl => {
        blockEl.style.marginTop = '0px';
        blockEl.style.marginBottom = '0px';
        blockEl.style.paddingTop = '0px';
        blockEl.style.paddingBottom = '0px';
        const contentEl = blockEl.querySelector('.editor-block__content');
        if (contentEl) {
          contentEl.style.marginTop = '0px';
          contentEl.style.marginBottom = '0px';
          contentEl.style.paddingTop = '0px';
          contentEl.style.paddingBottom = '0px';
          contentEl.style.paddingLeft = '24px';
        }
      });

      const refNode = container.children[insertIndex] || null;
      container.insertBefore(listEl, refNode);
    });
  }

  function initToolbar() {
    const toolbar = document.getElementById('editorToolbar');
    const textSelect = document.getElementById('textTypeSelect');

    toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-command]');
      if (!btn) return;
      const command = btn.dataset.command;
      document.execCommand(command, false, null);
      pushHistory();
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
      pushHistory();
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
      applyListToSelection('ul');
    });

    document.getElementById('insertOrderedList').addEventListener('click', () => {
      applyListToSelection('ol');
    });

    document.getElementById('clearListBtn').addEventListener('click', () => {
      clearListFromSelection();
    });

    document.getElementById('insertImageToolbarBtn').addEventListener('click', () => {
      openGalleryModal('image');
    });

    document.getElementById('undoBtn')?.addEventListener('click', undo);
    document.getElementById('redoBtn')?.addEventListener('click', redo);
  }

  function initPageNav() {
    document.getElementById('prevPageBtn').addEventListener('click', () => {
      const current = window.__currentPageIndex || 0;
      if (current > 0) {
        window.__currentPageIndex = current - 1;
        activeBlockId = null;
        updateSettingsPanel();
        renderCurrentPage();
        updateNavPanel();
      }
    });

    document.getElementById('nextPageBtn').addEventListener('click', () => {
      const current = window.__currentPageIndex || 0;
      if (current < pages.length - 1) {
        window.__currentPageIndex = current + 1;
        activeBlockId = null;
        updateSettingsPanel();
        renderCurrentPage();
        updateNavPanel();
      }
    });
  }

  let galleryOnSelect = null;

  async function openGalleryModal(mode, onSelect) {
    const modal = document.getElementById('imageGalleryModal');
    const grid = document.getElementById('galleryGrid');
    galleryOnSelect = typeof onSelect === 'function' ? onSelect : null;
    modal.style.display = 'flex';
    await renderGalleryGrid(mode, {});
  }

  async function renderGalleryGrid(mode, filters) {
    const grid = document.getElementById('galleryGrid');
    grid.innerHTML = '<p>Loading images...</p>';
    try {
      const params = new URLSearchParams();
      if (filters.tag) params.set('tag', filters.tag);
      if (filters.category) params.set('category', filters.category);
      if (filters.q) params.set('q', filters.q);
      const res = await fetch('/quote_editor/images?' + params.toString());
      const data = await res.json();
      const images = data.images || [];
      const tags = data.tags || [];
      const categories = data.categories || [];

      // Populate filter dropdowns (preserve current selection)
      const tagSel = document.getElementById('galleryTagFilter');
      const catSel = document.getElementById('galleryCategoryFilter');
      if (tagSel) {
        const cur = tagSel.value;
        tagSel.innerHTML = '<option value="">All tags</option>' + tags.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
        tagSel.value = cur;
      }
      if (catSel) {
        const cur = catSel.value;
        catSel.innerHTML = '<option value="">All categories</option>' + categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
        catSel.value = cur;
      }

      if (!images.length) {
        grid.innerHTML = '<p>No images available. Upload one below.</p>';
        return;
      }
      grid.innerHTML = images.map(img => {
        const tagsHtml = (img.tags || []).map(t => `<span class="gallery-tag">${escapeHtml(t)}</span>`).join('');
        return `
        <div class="gallery-item" data-url="${escapeHtml(img.url)}" data-filename="${escapeHtml(img.filename || '')}">
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.original_name || img.filename)}">
          <div class="gallery-item__name">${escapeHtml(img.original_name || img.filename)}</div>
          <div class="gallery-item__tags">${tagsHtml}</div>
        </div>`;
      }).join('');
      grid.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', () => {
          const url = item.dataset.url;
          const filename = item.dataset.filename;
          if (galleryOnSelect) {
            galleryOnSelect({ url, filename });
            document.getElementById('imageGalleryModal').style.display = 'none';
            return;
          }
          if (mode === 'image_group') {
            addBlock({
              type: 'image_group',
              snapshot: { images: [{ url, filename }], columns: 2 },
            });
          } else {
            addBlock({
              type: 'image',
              snapshot: { url, filename },
            });
          }
          document.getElementById('imageGalleryModal').style.display = 'none';
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
      formData.append('tags', document.getElementById('galleryTagsInput')?.value || '');
      formData.append('category', document.getElementById('galleryCategoryInput')?.value || '');
      try {
        const res = await fetch('/quote_editor/upload-image', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
          await renderGalleryGrid('image', {});
        }
      } catch (err) {
        alert('Upload failed');
      }
    });

    // Filter bar wiring
    const search = document.getElementById('gallerySearchInput');
    const tagSel = document.getElementById('galleryTagFilter');
    const catSel = document.getElementById('galleryCategoryFilter');
    const applyFilters = async () => {
      const filters = {
        q: search?.value || '',
        tag: tagSel?.value || '',
        category: catSel?.value || '',
      };
      await renderGalleryGrid('image', filters);
    };
    search?.addEventListener('input', applyFilters);
    tagSel?.addEventListener('change', applyFilters);
    catSel?.addEventListener('change', applyFilters);
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
        const settings = layout.settings_json || {};
        if (settings.document_styles) {
          documentStyles = { ...documentStyles, ...settings.document_styles };
        }
      }
    } catch (err) {
      alert('Failed to load layout');
    }
  }

  function collectBlocks() {
    return blocks.map(b => ({
      id: b.id,
      type: b.type,
      source_page: b.source_page || '',
      source_block_id: b.source_block_id || '',
      list_group_id: b.list_group_id || null,
      list_type: b.list_type || 'ul',
      list_index: b.list_index || 0,
      snapshot: b.snapshot || {},
      editor_overrides: b.editor_overrides || {},
      flags: b.flags || {},
      settings: b.settings || {},
    }));
  }

  function collectDocumentStyles() {
    const typography = {};
    TYPO_ELEMENTS.forEach(el => {
      const prefix = 'docTypo_' + el;
      typography[el] = {
        family: document.getElementById(prefix + '_family')?.value || documentStyles.typography[el].family,
        weight: document.getElementById(prefix + '_weight')?.value || documentStyles.typography[el].weight,
        size: parseInt(document.getElementById(prefix + '_size')?.value, 10) || documentStyles.typography[el].size,
        bold: document.getElementById(prefix + '_bold')?.checked || false,
        italic: document.getElementById(prefix + '_italic')?.checked || false,
        underline: document.getElementById(prefix + '_underline')?.checked || false,
        color: document.getElementById(prefix + '_color')?.value || documentStyles.typography[el].color,
      };
    });
    const header = documentStyles.header || {};
    const footer = documentStyles.footer || {};
    return {
      font_family: document.getElementById('docFontFamily')?.value || documentStyles.font_family,
      font_size_base: parseInt(document.getElementById('docFontSizeBase')?.value, 10) || documentStyles.font_size_base,
      header_font_size: parseInt(document.getElementById('docHeaderFontSize')?.value, 10) || documentStyles.header_font_size,
      footer_font_size: parseInt(document.getElementById('docFooterFontSize')?.value, 10) || documentStyles.footer_font_size,
      page_size: document.getElementById('docPageSize')?.value || documentStyles.page_size,
      header: {
        enabled: document.getElementById('docHeaderEnabled')?.checked ?? header.enabled ?? true,
        document_id_type: document.getElementById('docHeaderDocIdType')?.value || header.document_id_type || 'quote_number',
        document_id_manual: document.getElementById('docHeaderDocIdManual')?.value || header.document_id_manual || '',
        logo_url: document.getElementById('docHeaderLogoUrl')?.value || header.logo_url || '',
        logo_width: parseInt(document.getElementById('docHeaderLogoWidth')?.value, 10) || header.logo_width || 120,
        logo_height: parseInt(document.getElementById('docHeaderLogoHeight')?.value, 10) || header.logo_height || 40,
        logo_alignment: document.getElementById('docHeaderLogoAlign')?.value || header.logo_alignment || 'center',
        doc_id_alignment: document.getElementById('docHeaderDocIdAlign')?.value || header.doc_id_alignment || 'center',
        divider_style: document.getElementById('docHeaderDividerStyle')?.value || header.divider_style || 'single',
        divider_thickness: parseFloat(document.getElementById('docHeaderDividerThickness')?.value) || header.divider_thickness || 1,
        preset_padding: parseInt(document.getElementById('docHeaderPreset')?.value, 10) || header.preset_padding || 15,
        hide_on_cover: document.getElementById('docHeaderHideCover')?.checked || false,
      },
      footer: {
        enabled: document.getElementById('docFooterEnabled')?.checked ?? footer.enabled ?? true,
        divider_style: document.getElementById('docFooterDividerStyle')?.value || footer.divider_style || 'single',
        divider_thickness: parseFloat(document.getElementById('docFooterDividerThickness')?.value) || footer.divider_thickness || 1,
        page_number_mode: document.getElementById('docFooterPageNumber')?.value || footer.page_number_mode || 'on',
        page_number_alignment: document.getElementById('docFooterPageNumberAlign')?.value || footer.page_number_alignment || 'center',
        preset_padding: parseInt(document.getElementById('docFooterPreset')?.value, 10) || footer.preset_padding || 40,
        hide_on_cover: document.getElementById('docFooterHideCover')?.checked || false,
      },
      margins: {
        margin_top: parseInt(document.getElementById('docMarginTop')?.value, 10) || documentStyles.margins.margin_top,
        margin_bottom: parseInt(document.getElementById('docMarginBottom')?.value, 10) || documentStyles.margins.margin_bottom,
        margin_left: parseInt(document.getElementById('docMarginLeft')?.value, 10) || documentStyles.margins.margin_left,
        margin_right: parseInt(document.getElementById('docMarginRight')?.value, 10) || documentStyles.margins.margin_right,
      },
      typography,
      tables: {
        border: document.getElementById('docTableBorder')?.value || documentStyles.tables.border,
        header_bg: document.getElementById('docTableHeaderBg')?.value || documentStyles.tables.header_bg,
        row_bg: document.getElementById('docTableRowBg')?.value || documentStyles.tables.row_bg,
        alt_row_bg: document.getElementById('docTableAltRowBg')?.value || documentStyles.tables.alt_row_bg,
        font_size: parseInt(document.getElementById('docTableFontSize')?.value, 10) || documentStyles.tables.font_size,
      },
      images: {
        frame: document.getElementById('docImageFrame')?.value || documentStyles.images.frame,
        shadow: document.getElementById('docImageShadow')?.checked || false,
      },
      links: {
        color: document.getElementById('docLinkColor')?.value || documentStyles.links.color,
        underline: document.getElementById('docLinkUnderline')?.checked || false,
      },
    };
  }

  function applyDocumentStylesToEditor() {
    documentStyles = { ...documentStyles, ...collectDocumentStyles() };
  }

  async function quickSave() {
    const name = currentQuoteId ? `Quote ${currentQuoteId}` : 'Untitled Quote';
    const payload = {
      name,
      blocks_json: collectBlocks(),
      settings_json: { document_styles: collectDocumentStyles() },
      is_default: false,
    };
    try {
      const isUpdate = !!currentQuoteId;
      const url = isUpdate ? `/quote_editor/quotes/${currentQuoteId}` : '/quote_editor/quotes';
      const method = isUpdate ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        if (!isUpdate && data.quote && data.quote.id) {
          currentQuoteId = data.quote.id;
        }
        alert('Quote saved');
        refreshLayoutSelector();
      } else {
        alert('Save failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  function openSaveAsQuoteModal() {
    document.getElementById('saveAsQuoteModal').style.display = 'flex';
    document.getElementById('saveAsQuoteNameInput').value = '';
    loadSaveAsQuotesList();
  }

  async function loadSaveAsQuotesList() {
    const container = document.getElementById('saveAsQuotesList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/quotes');
      const data = await res.json();
      const quotes = data.quotes || [];
      if (!quotes.length) {
        container.innerHTML = '<p>No saved quotes yet. Enter a name below to create a new quote.</p>';
        return;
      }
      container.innerHTML = quotes.map(q => `
        <div class="quote-list-item" style="cursor:pointer;" data-overwrite-quote="${q.id}">
          <div><strong>${escapeHtml(q.name)}</strong> <small>${escapeHtml(q.client_name || '')}</small></div>
          <div style="font-size:0.85rem; color:#666;">Click to overwrite</div>
        </div>
      `).join('');
      container.querySelectorAll('[data-overwrite-quote]').forEach(item => {
        item.addEventListener('click', () => {
          const id = item.dataset.overwriteQuote;
          document.getElementById('saveAsQuoteNameInput').value = item.querySelector('strong').textContent;
          if (confirm('Overwrite this quote?')) {
            saveQuote(id);
          }
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load quotes.</p>';
    }
  }

  async function confirmSaveAsQuote() {
    const name = document.getElementById('saveAsQuoteNameInput').value.trim();
    if (!name) return alert('Quote name is required');
    await saveQuote(null, name);
  }

  async function saveQuote(existingId, name) {
    const quoteName = name || document.getElementById('saveAsQuoteNameInput').value.trim();
    if (!quoteName) return alert('Quote name is required');
    const payload = {
      name: quoteName,
      blocks_json: collectBlocks(),
      settings_json: { document_styles: collectDocumentStyles() },
      is_default: false,
    };
    try {
      const url = existingId ? `/quote_editor/quotes/${existingId}` : '/quote_editor/quotes';
      const method = existingId ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Quote saved');
        document.getElementById('saveAsQuoteModal').style.display = 'none';
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
    loadThemesList();
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
            currentQuoteId = id;
            const stylesOnly = document.getElementById('loadStylesOnlyCheckbox')?.checked;
            const quote = d.quote || {};
            const settings = quote.settings_json || {};
            if (settings.document_styles) {
              documentStyles = { ...documentStyles, ...settings.document_styles };
            }
            updateStylesFormFromDocumentStyles();
            if (!stylesOnly) {
              blocks = [];
              activeBlockId = null;
              updateSettingsPanel();
              const blist = quote.blocks_json || [];
              blist.forEach(b => addBlock(b));
            }
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
            const stylesOnly = document.getElementById('loadStylesOnlyCheckbox')?.checked;
            const layout = d.layout || {};
            const settings = layout.settings_json || {};
            if (settings.document_styles) {
              documentStyles = { ...documentStyles, ...settings.document_styles };
            }
            updateStylesFormFromDocumentStyles();
            if (!stylesOnly) {
              blocks = [];
              activeBlockId = null;
              updateSettingsPanel();
              const blist = layout.blocks_json || [];
              blist.forEach(b => addBlock(b));
            }
            document.getElementById('loadModal').style.display = 'none';
          }
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load templates.</p>';
    }
  }

  async function loadThemesList() {
    const container = document.getElementById('loadThemesList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/themes');
      const data = await res.json();
      const themes = data.themes || [];
      if (!themes.length) {
        container.innerHTML = '<p>No themes saved.</p>';
        return;
      }
      container.innerHTML = themes.map(t => `
        <div class="quote-list-item">
          <div><strong>${escapeHtml(t.name)}</strong> ${t.is_default ? '(Default)' : ''}</div>
          <div><button data-load-theme="${escapeHtml(t.name)}">Load</button></div>
        </div>
      `).join('');
      container.querySelectorAll('[data-load-theme]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const name = btn.dataset.loadTheme;
          const r = await fetch(`/quote_editor/themes/${encodeURIComponent(name)}`);
          const d = await r.json();
          if (d.success && d.theme) {
            const settings = d.theme.settings || {};
            if (settings.document_styles) {
              documentStyles = { ...documentStyles, ...settings.document_styles };
            }
            updateStylesFormFromDocumentStyles();
            document.getElementById('loadModal').style.display = 'none';
          }
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load themes.</p>';
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
    updatePreviewResizeBanner();
  }

  function closePreviewModal() {
    document.getElementById('previewModal').style.display = 'none';
  }

  function updatePreviewResizeBanner() {
    const banner = document.getElementById('previewResizeBanner');
    if (!banner) return;
    const viewport = document.getElementById('previewViewport');
    const page = document.getElementById('previewPage');
    if (!viewport || !page) return;
    const pageStyle = window.getComputedStyle(page);
    const maxWidth = parseFloat(pageStyle.maxWidth);
    const isSqueezed = viewport.clientWidth < maxWidth - 1;
    banner.style.display = isSqueezed ? 'block' : 'none';
  }

  function renderPreviewPage() {
    const pageBlocks = pages[previewPageIndex] || [];
    document.getElementById('previewPageNum').textContent = previewPageIndex + 1;
    document.getElementById('previewPrevBtn').disabled = previewPageIndex === 0;
    document.getElementById('previewNextBtn').disabled = previewPageIndex >= pages.length - 1;

    const ff = documentStyles.font_family || 'Arial, sans-serif';
    const baseSize = documentStyles.font_size_base || 16;
    let html = `<style>.preview-page { font-family: ${ff}; font-size: ${baseSize}px; }</style>`;

    html += renderPreviewHeader();

    html += '<div class="preview-page__body">';
    const renderedGroups = new Set();
    pageBlocks.forEach(block => {
      const gid = block.list_group_id;
      if (!gid) {
        html += renderPreviewBlock(block);
        return;
      }
      if (renderedGroups.has(gid)) return;
      renderedGroups.add(gid);

      const groupBlocks = pageBlocks.filter(b => b.list_group_id === gid);
      const listType = groupBlocks[0].list_type || 'ul';
      html += `<${listType} class="preview-list-group">`;
      groupBlocks.forEach(gBlock => {
        html += renderPreviewListItem(gBlock);
      });
      html += `</${listType}>`;
    });
    html += '</div>';

    html += renderPreviewFooter();

    document.getElementById('previewPage').innerHTML = html || '<p style="text-align:center; color:#999; padding:40px;">This page is empty.</p>';
  }

  function renderPreviewHeader() {
    const hdr = documentStyles.header || {};
    if (!hdr.enabled) return '';
    const fs = documentStyles.header_font_size || 10;
    const logoAlign = hdr.logo_alignment || 'center';
    const docIdAlign = hdr.doc_id_alignment || 'center';
    const logoMarginLeft = logoAlign === 'left' ? '0' : 'auto';
    const logoMarginRight = logoAlign === 'right' ? '0' : 'auto';
    const padding = hdr.preset_padding || 15;
    const pageMargins = documentStyles.margins || {};
    const ml = pageMargins.margin_left || 0;
    const mr = pageMargins.margin_right || 0;
    let html = `<div class="preview-header" style="font-size:${fs}px; top:${padding}px; left:${ml}px; right:${mr}px;">`;

    if (hdr.logo_url) {
      html += `<img src="${escapeHtml(hdr.logo_url)}" style="max-width:${hdr.logo_width || 120}px; max-height:${hdr.logo_height || 40}px; display:block; margin:0 ${logoMarginRight} 4px ${logoMarginLeft}; object-fit:contain;" />`;
    }

    const docIdType = hdr.document_id_type || 'quote_number';
    let docIdText = '';
    if (docIdType === 'customer_address') {
      docIdText = '{{client_address}}';
    } else if (docIdType === 'quote_number') {
      docIdText = '{{quote_ref}}';
    } else if (docIdType === 'manual') {
      docIdText = escapeHtml(hdr.document_id_manual || '');
    }
    if (docIdText) {
      html += `<div class="preview-doc-id" style="text-align:${docIdAlign};">${docIdText}</div>`;
    }

    html += renderPreviewDivider(hdr.divider_style, hdr.divider_thickness);
    html += `</div>`;
    return html;
  }

  function renderPreviewFooter() {
    const ftr = documentStyles.footer || {};
    if (!ftr.enabled) return '';
    const fs = documentStyles.footer_font_size || 8;
    const pageNumAlign = ftr.page_number_alignment || 'center';
    const padding = ftr.preset_padding || 40;
    const pageMargins = documentStyles.margins || {};
    const marginLeft = pageMargins.margin_left || 0;
    const marginRight = pageMargins.margin_right || 0;
    let html = `<div class="preview-footer" style="font-size:${fs}px; bottom:${padding}px; left:${marginLeft}px; right:${marginRight}px;">`;

    html += renderPreviewDivider(ftr.divider_style, ftr.divider_thickness);

    if (ftr.page_number_mode && ftr.page_number_mode !== 'off') {
      const pageLabel = previewPageIndex === 0 && ftr.page_number_mode === 'skip_first'
        ? 'Page (hidden on first)'
        : `Page ${previewPageIndex + 1}`;
      html += `<div class="preview-page-num" style="text-align:${pageNumAlign};">${pageLabel}</div>`;
    }

    html += `</div>`;
    return html;
  }

  function renderPreviewDivider(style, thickness) {
    const t = parseFloat(thickness) || 1;
    if (!style || style === 'none') return '';
    const borderTop = `${t}px`;
    let borderStyle = 'solid';
    let extra = '';
    switch (style) {
      case 'japanese_dots':
        borderStyle = 'dotted';
        break;
      case 'double':
        borderStyle = 'double';
        break;
      case 'circles':
        borderStyle = 'dotted';
        extra = 'border-top-style: round;';
        break;
      default:
        borderStyle = 'solid';
    }
    return `<hr class="preview-divider" style="border:none; border-top-width:${borderTop}; border-top-style:${borderStyle}; ${extra} border-top-color:#000; margin:4px 0;" />`;
  }

  function previewTypoStyle(blockType) {
    const typo = documentStyles.typography || {};
    const typeMap = { page_title: 'h1', page_heading: 'h1', category_title: 'h2', form_question: 'para', notes: 'notes', guide: 'guide', guidance: 'guidance' };
    const key = typeMap[blockType];
    const defaults = { family: '', weight: '', size: 14, bold: false, italic: false, underline: false, color: '' };
    const t = key ? { ...defaults, ...(typo[key] || {}) } : null;
    if (!t) return '';
    const ff = documentStyles.font_family || 'Arial, sans-serif';
    const baseSize = documentStyles.font_size_base || 16;
    const parts = [];
    if (t.family) parts.push(`font-family:${t.family}`);
    else if (ff) parts.push(`font-family:${ff}`);
    if (t.size) parts.push(`font-size:${t.size}px`);
    if (t.color) parts.push(`color:${t.color}`);
    if (t.bold) parts.push('font-weight:bold');
    else if (t.weight) parts.push(`font-weight:${t.weight}`);
    if (t.italic) parts.push('font-style:italic');
    if (t.underline) parts.push('text-decoration:underline');
    return parts.join(';');
  }

  function previewMergedStyle(blockType, extra) {
    const ts = previewTypoStyle(blockType);
    const combined = [ts, extra].filter(Boolean).join(';');
    return combined ? ` style="${combined}"` : '';
  }

  function renderPreviewBlock(block) {
    const snapshot = block.snapshot || {};
    const settings = block.settings || {};
    const marginTop = settings.margin_top || 0;
    const marginBottom = settings.margin_bottom || 0;
    const padding = settings.padding || 0;
    const alignment = settings.alignment || 'left';

    if (block.type === 'page_heading') {
      return `<h1${previewMergedStyle('page_heading', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};`)}>${escapeHtml(snapshot.title || '')}</h1>`;
    } else if (block.type === 'page_title') {
      return '';
    } else if (block.type === 'category_title') {
      return `<h2${previewMergedStyle('category_title', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};`)}>${escapeHtml(snapshot.title || '')}</h2>`;
    } else if (block.type === 'form_question') {
      const overrideContent = (block.editor_overrides || {}).content;
      const hasContent = typeof overrideContent === 'string' && overrideContent.trim();
      const label = escapeHtml(snapshot.label || '');
      const value = escapeHtml(snapshot.value || '');
      const guidance = escapeHtml(snapshot.output_guidance || '');
      let bodyHtml;
      if (hasContent) {
        bodyHtml = overrideContent;
      } else {
        const titlePart = label ? `<strong>${label}:</strong> ${value}` : value;
        const guidanceBlock = guidance ? `<div class="preview-guidance"${previewMergedStyle('guidance', '')}>${guidance}</div>` : '';
        bodyHtml = `${titlePart}${guidanceBlock}`;
      }
      return `<div class="preview-question"${previewMergedStyle('form_question', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};`)}>${bodyHtml}</div>`;
    } else if (block.type === 'calculator') {
      const groups = snapshot.groups || [];
      if (groups.length) {
        let calcHtml = `<div class="preview-calculator" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px;"><table class="calc-table"><thead><tr><th>Item</th><th>Total</th></tr></thead><tbody>`;
        groups.forEach(g => {
          (g.items || []).forEach(item => {
            calcHtml += `<tr><td>${escapeHtml(item.output_title || '')}</td><td>${item.line_total?.toFixed(2) || '0.00'}</td></tr>`;
          });
        });
        calcHtml += `</tbody></table><p><strong>Grand Total: ${snapshot.grand_total?.toFixed(2) || '0.00'}</strong></p></div>`;
        return calcHtml;
      }
      return '';
    } else if (block.type === 'notes') {
      const overrideContent = (block.editor_overrides || {}).content;
      const hasContent = typeof overrideContent === 'string' && overrideContent.trim();
      return `<div class="preview-notes"${previewMergedStyle('notes', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px;`)}>${hasContent ? overrideContent : (snapshot.content || '')}</div>`;
    } else if (block.type === 'page_break') {
      return `<div style="page-break-before: always; margin-top:${marginTop}px; margin-bottom:${marginBottom}px;"></div>`;
    } else if (block.type === 'image') {
      const url = snapshot.url || '';
      if (url) {
        return `<div class="preview-image" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; text-align:${alignment};"><img src="${escapeHtml(url)}" style="max-width:100%; height:auto;" /></div>`;
      }
      return '';
    } else if (block.type === 'image_group') {
      const images = snapshot.images || [];
      const cols = snapshot.columns || 2;
      if (images.length) {
        let groupHtml = `<div class="preview-image-group" style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:${padding}px; display:grid; grid-template-columns: repeat(${cols}, 1fr); gap:8px;">`;
        images.forEach(img => {
          groupHtml += `<img src="${escapeHtml(img.url || '')}" style="width:100%; height:auto;" />`;
        });
        groupHtml += `</div>`;
        return groupHtml;
      }
      return '';
    }
    return '';
  }

  function renderPreviewListItem(block) {
    const snapshot = block.snapshot || {};
    const settings = block.settings || {};
    const marginTop = 0;
    const marginBottom = 0;
    const padding = 0;
    const alignment = settings.alignment || 'left';

    if (block.type === 'form_question') {
      const overrideContent = (block.editor_overrides || {}).content;
      const hasContent = typeof overrideContent === 'string' && overrideContent.trim();
      const label = escapeHtml(snapshot.label || '');
      const value = escapeHtml(snapshot.value || '');
      const guidance = escapeHtml(snapshot.output_guidance || '');
      let bodyHtml;
      if (hasContent) {
        bodyHtml = overrideContent;
      } else {
        const titlePart = label ? `<strong>${label}:</strong> ${value}` : value;
        const guidanceBlock = guidance ? `<div class="preview-guidance"${previewMergedStyle('guidance', '')}>${guidance}</div>` : '';
        bodyHtml = `${titlePart}${guidanceBlock}`;
      }
      return `<li${previewMergedStyle('form_question', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0; padding-left:24px; text-align:${alignment};`)}>${bodyHtml}</li>`;
    } else if (block.type === 'notes') {
      const overrideContent = (block.editor_overrides || {}).content;
      const hasContent = typeof overrideContent === 'string' && overrideContent.trim();
      return `<li${previewMergedStyle('notes', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0; padding-left:24px;`)}>${hasContent ? overrideContent : (snapshot.content || '')}</li>`;
    } else if (block.type === 'page_heading') {
      return `<li${previewMergedStyle('page_heading', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0; text-align:${alignment};`)}><h1>${escapeHtml(snapshot.title || '')}</h1></li>`;
    } else if (block.type === 'page_title') {
      return '';
    } else if (block.type === 'category_title') {
      const catImg = snapshot.category_image
        ? `<img src="${escapeHtml(snapshot.category_image)}" alt="" style="max-width:200px;max-height:120px;display:block;margin-bottom:8px;border-radius:4px;">`
        : '';
      return `<li${previewMergedStyle('category_title', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0; text-align:${alignment};`)}>${catImg}<h2>${escapeHtml(snapshot.title || '')}</h2></li>`;
    } else if (block.type === 'page_break') {
      return `<li${previewMergedStyle('page_break', `margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0;`)}><div style="page-break-before: always;"></div></li>`;
    } else {
      const bodyHtml = renderBlockContent(block);
      return `<li style="margin-top:${marginTop}px; margin-bottom:${marginBottom}px; padding:0; text-align:${alignment};">${bodyHtml}</li>`;
    }
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

  function updateStylesFormFromDocumentStyles() {
    const fields = {
      docFontFamily: documentStyles.font_family,
      docFontSizeBase: documentStyles.font_size_base,
      docHeaderFontSize: documentStyles.header_font_size,
      docFooterFontSize: documentStyles.footer_font_size,
      docPageSize: documentStyles.page_size,
      docTableBorder: documentStyles.tables.border,
      docTableHeaderBg: documentStyles.tables.header_bg,
      docTableRowBg: documentStyles.tables.row_bg,
      docTableAltRowBg: documentStyles.tables.alt_row_bg,
      docTableFontSize: documentStyles.tables.font_size,
      docImageFrame: documentStyles.images.frame,
      docLinkColor: documentStyles.links.color,
    };
    Object.entries(fields).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    });
    const checkboxes = {
      docImageShadow: documentStyles.images.shadow,
      docLinkUnderline: documentStyles.links.underline,
    };
    Object.entries(checkboxes).forEach(([id, checked]) => {
      const el = document.getElementById(id);
      if (el) el.checked = checked;
    });
    const margins = documentStyles.margins || {};
    const marginFields = {
      docMarginTop: margins.margin_top,
      docMarginBottom: margins.margin_bottom,
      docMarginLeft: margins.margin_left,
      docMarginRight: margins.margin_right,
    };
    Object.entries(marginFields).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    });
    TYPO_ELEMENTS.forEach(el => {
      const prefix = 'docTypo_' + el;
      const t = documentStyles.typography[el] || {};
      const map = {
        family: t.family || '',
        weight: t.weight || '',
        size: t.size || 16,
        bold: t.bold || false,
        italic: t.italic || false,
        underline: t.underline || false,
        color: t.color || '#000000',
      };
      Object.entries(map).forEach(([suffix, value]) => {
        const field = document.getElementById(prefix + '_' + suffix);
        if (!field) return;
        if (field.type === 'checkbox') field.checked = value;
        else field.value = value;
      });
    });

    const hdr = documentStyles.header || {};
    const ftr = documentStyles.footer || {};
    const hdrFields = {
      docHeaderEnabled: hdr.enabled ?? true,
      docHeaderDocIdType: hdr.document_id_type || 'quote_number',
      docHeaderDocIdManual: hdr.document_id_manual || '',
      docHeaderDocIdAlign: hdr.doc_id_alignment || 'center',
      docHeaderLogoUrl: hdr.logo_url || '',
      docHeaderLogoWidth: hdr.logo_width || 120,
      docHeaderLogoHeight: hdr.logo_height || 40,
      docHeaderLogoAlign: hdr.logo_alignment || 'center',
      docHeaderDividerStyle: hdr.divider_style || 'single',
      docHeaderDividerThickness: hdr.divider_thickness ?? 1,
      docHeaderPreset: hdr.preset_padding ?? 15,
      docHeaderHideCover: hdr.hide_on_cover ?? false,
    };
    Object.entries(hdrFields).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (el.type === 'checkbox') el.checked = value;
      else el.value = value;
    });

    const existingLogoUrl = (hdr.logo_url || '').trim();
    const logoPreviewImg = document.getElementById('docHeaderLogoPreviewImg');
    const logoPreviewPlaceholder = document.getElementById('docHeaderLogoPreviewPlaceholder');
    const docIdTypeEl = document.getElementById('docHeaderDocIdType');
    const manualIdLabel = document.getElementById('docHeaderDocIdManualLabel');
    if (logoPreviewImg) {
      if (existingLogoUrl) {
        logoPreviewImg.src = existingLogoUrl;
        logoPreviewImg.style.display = 'block';
      } else {
        logoPreviewImg.src = '';
        logoPreviewImg.style.display = 'none';
      }
    }
    if (logoPreviewPlaceholder) {
      logoPreviewPlaceholder.style.display = existingLogoUrl ? 'none' : 'inline';
    }

    if (docIdTypeEl) {
      const showManual = docIdTypeEl.value === 'manual';
      if (manualIdLabel) manualIdLabel.style.display = showManual ? 'flex' : 'none';
    }

    const ftrFields = {
      docFooterEnabled: ftr.enabled ?? true,
      docFooterDividerStyle: ftr.divider_style || 'single',
      docFooterDividerThickness: ftr.divider_thickness ?? 1,
      docFooterPageNumber: ftr.page_number_mode || 'on',
      docFooterPageNumberAlign: ftr.page_number_alignment || 'center',
      docFooterPreset: ftr.preset_padding || 40,
      docFooterHideCover: ftr.hide_on_cover ?? false,
    };
    Object.entries(ftrFields).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (el.type === 'checkbox') el.checked = value;
      else el.value = value;
    });
  }

  function openStylesModal() {
    document.getElementById('stylesModal').style.display = 'flex';
    updateStylesFormFromDocumentStyles();
  }

  function closeStylesModal() {
    document.getElementById('stylesModal').style.display = 'none';
  }

  function confirmStyles() {
    documentStyles = collectDocumentStyles();
    closeStylesModal();
  }

  function buildTypographyRows() {
    const container = document.getElementById('typographyRows');
    if (!container) return;
    let html = '';
    TYPO_ELEMENTS.forEach(el => {
      const prefix = 'docTypo_' + el;
      const familyOpts = FONT_FAMILIES.map(f => `<option value="${f.value}">${f.label}</option>`).join('');
      const weightOpts = FONT_WEIGHTS.map(w => `<option value="${w.value}">${w.label}</option>`).join('');
      html += `
        <div class="typography-row">
          <div class="typography-row__label">${TYPO_LABELS[el]}</div>
          <div class="typography-row__controls">
            <select id="${prefix}_family" title="Font family">${familyOpts}</select>
            <select id="${prefix}_weight" title="Weight">${weightOpts}</select>
            <input type="number" id="${prefix}_size" min="8" max="72" title="Size (px)" style="width:64px;">
            <label class="chk" title="Bold"><input type="checkbox" id="${prefix}_bold">B</label>
            <label class="chk" title="Italic"><input type="checkbox" id="${prefix}_italic"><em>I</em></label>
            <label class="chk" title="Underline"><input type="checkbox" id="${prefix}_underline"><u>U</u></label>
            <input type="color" id="${prefix}_color" title="Color" value="#000000" style="width:32px; height:32px; border:1px solid #ccc; border-radius:4px; cursor:pointer; padding:0;">
          </div>
        </div>`;
    });
    container.innerHTML = html;
  }

  function initStylesModal() {
    buildTypographyRows();
    document.getElementById('stylesBtn').addEventListener('click', openStylesModal);
    document.getElementById('closeStylesModal').addEventListener('click', closeStylesModal);
    document.getElementById('confirmStylesBtn').addEventListener('click', confirmStyles);
    document.getElementById('saveThemeBtn').addEventListener('click', openSaveThemeModal);
    document.getElementById('confirmSaveThemeBtn').addEventListener('click', confirmSaveTheme);
    document.getElementById('browseThemesBtn').addEventListener('click', openSaveAsThemeModal);
    document.getElementById('closeSaveThemeModal').addEventListener('click', () => {
      document.getElementById('saveThemeModal').style.display = 'none';
    });

    const logoWidthEl = document.getElementById('docHeaderLogoWidth');
    const logoHeightEl = document.getElementById('docHeaderLogoHeight');
    const docIdTypeEl = document.getElementById('docHeaderDocIdType');
    const manualIdLabel = document.getElementById('docHeaderDocIdManualLabel');
    let logoBaseRatio = 120 / 40;

    function updateLogoRatio(fromWidth) {
      const w = parseInt(logoWidthEl?.value, 10) || 120;
      const h = parseInt(logoHeightEl?.value, 10) || 40;
      if (fromWidth) {
        logoHeightEl.value = Math.max(10, Math.round(w / logoBaseRatio));
      } else {
        logoWidthEl.value = Math.max(20, Math.round(h * logoBaseRatio));
      }
    }
    function captureLogoRatio() {
      const w = parseInt(logoWidthEl?.value, 10) || 120;
      const h = parseInt(logoHeightEl?.value, 10) || 40;
      logoBaseRatio = w / (h || 1);
    }

    docIdTypeEl?.addEventListener('change', () => {
      const showManual = docIdTypeEl.value === 'manual';
      if (manualIdLabel) manualIdLabel.style.display = showManual ? 'flex' : 'none';
    });

    logoWidthEl?.addEventListener('focus', captureLogoRatio);
    logoWidthEl?.addEventListener('input', () => updateLogoRatio(true));
    logoHeightEl?.addEventListener('focus', captureLogoRatio);
    logoHeightEl?.addEventListener('input', () => updateLogoRatio(false));

    const logoFileEl = document.getElementById('docHeaderLogoFile');
    const logoUrlEl = document.getElementById('docHeaderLogoUrl');
    const logoUploadBtn = document.getElementById('docHeaderLogoUploadBtn');
    const logoPreviewImg = document.getElementById('docHeaderLogoPreviewImg');
    const logoPreviewPlaceholder = document.getElementById('docHeaderLogoPreviewPlaceholder');

    logoUploadBtn?.addEventListener('click', () => logoFileEl?.click());

    logoFileEl?.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tags', 'header-logo');
      formData.append('category', 'logos');
      try {
        const res = await fetch('/quote_editor/upload-image', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success && data.url) {
          logoUrlEl.value = data.url;
          if (data.width && data.height) {
            logoBaseRatio = data.width / data.height;
            logoWidthEl.value = Math.min(400, Math.max(20, data.width));
            logoHeightEl.value = Math.min(200, Math.max(10, data.height));
          }
          if (logoPreviewImg) {
            logoPreviewImg.src = data.url;
            logoPreviewImg.style.display = 'block';
          }
          if (logoPreviewPlaceholder) {
            logoPreviewPlaceholder.style.display = 'none';
          }
        }
      } catch (err) {
        alert('Logo upload failed');
      } finally {
        logoFileEl.value = '';
      }
    });

    document.querySelectorAll('.tab-btn[data-styles-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn[data-styles-tab]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.stylesTab;
        document.querySelectorAll('.styles-panel').forEach(p => p.style.display = 'none');
        const panel = document.getElementById('styles' + tab.charAt(0).toUpperCase() + tab.slice(1));
        if (panel) panel.style.display = 'block';
      });
    });

    const headerPreset = document.getElementById('docHeaderPreset');
    const footerPreset = document.getElementById('docFooterPreset');
    const updatePreviewFromStyles = () => {
      documentStyles = collectDocumentStyles();
      renderPreviewPage();
    };
    headerPreset?.addEventListener('change', updatePreviewFromStyles);
    footerPreset?.addEventListener('change', updatePreviewFromStyles);
  }

  function openSaveThemeModal() {
    document.getElementById('saveThemeModal').style.display = 'flex';
    document.getElementById('themeNameInput').value = '';
    document.getElementById('setAsDefaultCheckbox').checked = false;
  }

  async function confirmSaveTheme() {
    const name = document.getElementById('themeNameInput').value.trim();
    if (!name) return alert('Theme name is required');
    const isDefault = document.getElementById('setAsDefaultCheckbox').checked;
    const payload = {
      name,
      settings_json: { document_styles: collectDocumentStyles() },
      is_default: isDefault,
    };
    try {
      const res = await fetch('/quote_editor/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Theme saved');
        document.getElementById('saveThemeModal').style.display = 'none';
      } else {
        alert('Save failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  function openSaveAsThemeModal() {
    const modal = document.getElementById('saveAsThemeModal');
    modal.style.display = 'flex';
    document.getElementById('saveAsThemeNameInput').value = '';
    loadSaveAsThemesList();
  }

  async function loadSaveAsThemesList() {
    const container = document.getElementById('saveAsThemesList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/themes');
      const data = await res.json();
      const themes = data.themes || [];
      if (!themes.length) {
        container.innerHTML = '<p>No themes saved yet. Enter a name below to create a new theme.</p>';
        return;
      }
      container.innerHTML = themes.map(t => `
        <div class="quote-list-item" style="cursor:pointer;" data-overwrite-theme="${escapeHtml(t.name)}">
          <div><strong>${escapeHtml(t.name)}</strong> ${t.is_default ? '(Default)' : ''}</div>
          <div style="font-size:0.85rem; color:#666;">Click to overwrite</div>
        </div>
      `).join('');
      container.querySelectorAll('[data-overwrite-theme]').forEach(item => {
        item.addEventListener('click', () => {
          const name = item.dataset.overwriteTheme;
          document.getElementById('saveAsThemeNameInput').value = name;
          if (confirm(`Overwrite theme "${name}"?`)) {
            const isDefault = document.getElementById('setAsDefaultCheckbox').checked;
            saveTheme(name, isDefault);
          }
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load themes.</p>';
    }
  }

  async function confirmSaveAsTheme() {
    const name = document.getElementById('saveAsThemeNameInput').value.trim();
    if (!name) return alert('Theme name is required');
    const isDefault = document.getElementById('setAsDefaultCheckbox').checked;
    await saveTheme(name, isDefault);
  }

  async function saveTheme(name, isDefault) {
    const payload = {
      name,
      settings_json: { document_styles: collectDocumentStyles() },
      is_default: isDefault,
    };
    try {
      const res = await fetch('/quote_editor/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        alert('Theme saved');
        document.getElementById('saveAsThemeModal').style.display = 'none';
        document.getElementById('saveThemeModal').style.display = 'none';
      } else {
        alert('Save failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Save failed');
    }
  }

  function initModals() {
    document.getElementById('previewBtn').addEventListener('click', openPreviewModal);
    document.getElementById('saveBtn').addEventListener('click', quickSave);
    document.getElementById('saveAsBtn').addEventListener('click', openSaveAsQuoteModal);
    document.getElementById('loadBtn').addEventListener('click', openLoadModal);
    document.getElementById('exportBtn').addEventListener('click', openExportModal);
    document.getElementById('confirmSaveAsQuoteBtn').addEventListener('click', confirmSaveAsQuote);
    document.getElementById('closeSaveAsQuoteModal').addEventListener('click', () => {
      document.getElementById('saveAsQuoteModal').style.display = 'none';
    });
    document.getElementById('closeLoadModal').addEventListener('click', () => {
      document.getElementById('loadModal').style.display = 'none';
    });
    document.getElementById('closeExportModal').addEventListener('click', () => {
      document.getElementById('exportModal').style.display = 'none';
    });
    document.getElementById('exportPdfBtn').addEventListener('click', exportPDF);
    document.getElementById('exportDocxBtn').addEventListener('click', exportDOCX);
    document.getElementById('closePreviewModal').addEventListener('click', closePreviewModal);
    document.getElementById('confirmSaveAsThemeBtn').addEventListener('click', confirmSaveAsTheme);
    document.getElementById('closeSaveAsThemeModal').addEventListener('click', () => {
      document.getElementById('saveAsThemeModal').style.display = 'none';
    });

    document.querySelectorAll('#loadTabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#loadTabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.getElementById('loadQuotesList').style.display = tab === 'quotes' ? 'block' : 'none';
        document.getElementById('loadThemesList').style.display = tab === 'themes' ? 'block' : 'none';
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
            copiedSettings = { ...(block.settings || {}) };
            menu.style.display = 'none';
          } else if (action === 'paste-style') {
            if (copiedSettings && activeBlockId) {
              const targetBlock = blocks.find(b => b.id === activeBlockId);
              if (targetBlock) {
                targetBlock.settings = { ...copiedSettings };
                applyBlockStyles(targetBlock);
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
          <span>Advanced Controls</span>
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
          <label>Font Size
            <input type="number" data-setting="font_size" value="${settings.font_size || 16}" min="8" max="72">
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

    if (block.type === 'page_title' || block.type === 'page_heading' || block.type === 'category_title') {
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

    if (block.type === 'page_title') {
      const isHidden = !!block.flags?.hidden;
      html += `
        <div class="settings-block">
          <div class="settings-block__header">Page Visibility</div>
          <div class="settings-block__body">
            <label style="display:flex; align-items:center; gap:0.5rem; cursor:pointer;">
              <input type="checkbox" data-setting="hidden" ${isHidden ? 'checked' : ''}>
              <span>Hide this page from output</span>
            </label>
          </div>
        </div>
      `;
    }

    const content = block.editor_overrides?.content || block.snapshot?.content;
    if (content !== undefined && content !== null && block.type !== 'page_title' && block.type !== 'category_title') {
      const contentHtml = escapeHtml(content);
      html += `
        <div class="settings-block">
          <div class="settings-block__header">Content</div>
          <div class="settings-block__body">
            <label>Content
              <textarea data-setting="content" rows="4">${contentHtml}</textarea>
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
          pushHistory();
          block.snapshot = block.snapshot || {};
          block.snapshot.title = input.value;
          const contentEl = getBlockEl(block.id)?.querySelector('.editor-block__content');
          if (contentEl && block.type === 'page_heading') {
            contentEl.innerHTML = `<h1>${escapeHtml(input.value)}</h1>`;
          } else if (contentEl && block.type === 'page_title') {
            contentEl.innerHTML = '';
          } else if (contentEl && block.type === 'category_title') {
            contentEl.innerHTML = `<h2>${escapeHtml(input.value)}</h2>`;
          }
          return;
        }
        if (key === 'content') {
          pushHistory();
          block.editor_overrides = block.editor_overrides || {};
          block.editor_overrides.content = input.value;
          const contentEl = getBlockEl(block.id)?.querySelector('.editor-block__content');
          if (contentEl) {
            contentEl.innerHTML = input.value;
            block.flags = block.flags || {};
            block.flags.editor_dirty = true;
            const dot = getBlockEl(block.id)?.querySelector('.editor-block__source-dot');
            if (dot) dot.classList.add('editor-block__source-dot--editor');
          }
          return;
        }
        if (key === 'hidden') {
          pushHistory();
          block.flags = block.flags || {};
          block.flags.hidden = input.checked;
          const pageKey = block.source_page || block.id;
          blocks.forEach(b => {
            if (b.source_page === pageKey || b.id === pageKey) {
              if (b.type === 'page_title') {
                b.flags = b.flags || {};
                b.flags.hidden = input.checked;
                b.style = b.style || {};
                b.style.display = input.checked ? 'none' : '';
              } else if (b.type === 'page_heading') {
                b.style = b.style || {};
                b.style.display = input.checked ? 'none' : '';
              }
            }
          });
          renderCurrentPage();
          updateNavPanel();
          return;
        }
        pushHistory();
        block.settings = block.settings || {};
        block.settings[key] = input.type === 'number' ? parseInt(input.value, 10) || 0 : input.value;
        applyBlockStyles(block);
      });
    });
  }

  function updateNavPanel() {
    const panel = document.getElementById('navPanel');
    if (!panel) return;

    const pageGroups = [];
    let currentPage = null;

    blocks.forEach((block, index) => {
      const isPageSeparator = block.type === 'page_title' || block.type === 'page_break';

      if (isPageSeparator && currentPage !== null) {
        pageGroups.push(currentPage);
        currentPage = null;
      }

      if (!currentPage) {
        let title = 'Page ' + (pageGroups.length + 1);
        if (block.type === 'page_title') {
          title = block.snapshot.title || 'Untitled Page';
        }
        currentPage = { title, items: [] };
      }

      currentPage.items.push({ block, index });
    });

    if (currentPage) {
      pageGroups.push(currentPage);
    }

    if (pageGroups.length === 0) {
      panel.innerHTML = '<p class="editor-settings-placeholder">No blocks yet.</p>';
      return;
    }

    let html = '';

    pageGroups.forEach((page, pageIndex) => {
      const isActive = page.items.some(item => item.block.id === activeBlockId);
      const separator = page.items.find(item => item.block.type === 'page_title' || item.block.type === 'page_break');
      const isHidden = separator && separator.block.flags && separator.block.flags.hidden;

      html += `<div class="nav-page-group" data-page-index="${pageIndex}">`;
      html += `<div class="nav-page-header ${isActive ? 'nav-item--active' : ''}">`;
      html += `  <span class="nav-page-toggle">▸</span>`;
      html += `  <button class="nav-page-visibility" data-page-index="${pageIndex}" title="${isHidden ? 'Show page' : 'Hide page'}">`;
      html += `    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">`;
      if (isHidden) {
        html += `      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>`;
        html += `      <line x1="1" y1="1" x2="23" y2="23"/>`;
      } else {
        html += `      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>`;
        html += `      <circle cx="12" cy="12" r="3"/>`;
      }
      html += `    </svg>`;
      html += `  </button>`;
      html += `  <span class="nav-item__label">${escapeHtml(page.title)}</span>`;
      html += `</div>`;

      html += `<div class="nav-page-items nav-page-items--collapsed">`;

      page.items.forEach(({ block }) => {
        const snapshot = block.snapshot || {};

        if (block.type === 'page_title') {
          // Page title is the header, skip as nav item
        } else if (block.type === 'category_title') {
          const isActive = activeBlockId === block.id;
          html += `<div class="nav-item nav-item--category ${isActive ? 'nav-item--active' : ''}" data-block-id="${block.id}">
            <span class="nav-item__label">${escapeHtml(snapshot.title || 'Uncategorized')}</span>
          </div>`;
        } else if (block.type === 'form_question') {
          const label = snapshot.label || 'Question';
          const isActive = activeBlockId === block.id;
          html += `<div class="nav-item nav-item--question ${isActive ? 'nav-item--active' : ''}" data-block-id="${block.id}">
            <span class="nav-item__label">${escapeHtml(label)}</span>
          </div>`;
        } else if (block.type === 'page_break') {
          html += `<div class="nav-item nav-item--break" data-block-id="${block.id}">
            <span class="nav-item__label">Page Break</span>
          </div>`;
        }
      });

      html += `</div></div>`;
    });

    panel.innerHTML = html;

    // Page collapse/expand handlers
    panel.querySelectorAll('.nav-page-header').forEach(header => {
      header.addEventListener('click', (e) => {
        if (e.target.closest('.nav-page-visibility')) return;
        const group = header.closest('.nav-page-group');
        const items = group.querySelector('.nav-page-items');
        const toggle = header.querySelector('.nav-page-toggle');

        items.classList.toggle('nav-page-items--collapsed');
        toggle.textContent = items.classList.contains('nav-page-items--collapsed') ? '▸' : '▾';
      });
    });

    panel.querySelectorAll('.nav-page-visibility').forEach(btn => {
      btn.addEventListener('click', () => {
        const pageIndex = parseInt(btn.dataset.pageIndex, 10);
        const page = pageGroups[pageIndex];
        if (!page) return;
        const separator = page.items.find(item => item.block.type === 'page_title' || item.block.type === 'page_break');
        if (!separator) return;
        const pageKey = separator.block.source_page || separator.block.id;
        const newHidden = !(separator.block.flags && separator.block.flags.hidden);
        blocks.forEach(b => {
          if (b.source_page === pageKey || b.id === pageKey) {
            if (b.type === 'page_title') {
              b.flags = b.flags || {};
              b.flags.hidden = newHidden;
              b.style = b.style || {};
              b.style.display = newHidden ? 'none' : '';
            } else if (b.type === 'page_heading') {
              b.style = b.style || {};
              b.style.display = newHidden ? 'none' : '';
            }
          }
        });
        renderCurrentPage();
        updateNavPanel();
      });
    });

    // Nav item click handlers
    panel.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const blockId = item.dataset.blockId;
        if (!blockId) return;

        const block = blocks.find(b => b.id === blockId);
        if (!block) return;

        const blockIndex = blocks.indexOf(block);
        let targetPageIndex = 0;
        for (let i = 0; i <= blockIndex; i++) {
          if ((blocks[i].type === 'page_title' || blocks[i].type === 'page_break') && i > 0) {
            targetPageIndex++;
          }
        }

        window.__currentPageIndex = targetPageIndex;
        renderCurrentPage();
        setActiveBlock(blockId);
        updateNavHighlight();
      });
    });
  }

  function updateNavHighlight() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('nav-item--active');
      if (item.dataset.blockId === activeBlockId) {
        item.classList.add('nav-item--active');
        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
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
        if (type === 'page_break') {
          addBlock({ type: 'page_break' });
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

  function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const mod = isMac ? e.metaKey : e.ctrlKey;

      if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (mod && e.key.toLowerCase() === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      } else if (mod && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo();
      }
    });
    window.addEventListener('resize', updatePreviewResizeBanner);
  }

  async function init() {
     await checkPendingBlocks();
     refreshLayoutSelector();
     initToolbar();
     initPageNav();
     initPreviewNav();
     initGallery();
     initInsertButtons();
     initModals();
     initStylesModal();
     initOutsideClickClose();
     initContextMenu();
     initKeyboardShortcuts();
     pushHistory();
     updateNavPanel();
     updateSettingsPanel();
     const sidebar = document.getElementById('sidebar');
     const mainContent = document.querySelector('.main-content');
     if (sidebar && !sidebar.classList.contains('collapsed')) {
       sidebar.classList.add('collapsed');
     }
     if (mainContent && !mainContent.classList.contains('expanded')) {
       mainContent.classList.add('expanded');
     }
   }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
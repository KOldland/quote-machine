(function () {
  'use strict';

  // Shared image picker for use outside the Quote Editor (e.g. Builder mode).
  // Exposes window.QuoteGallery.open(onSelect) where onSelect({url, filename}).

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  let modalEl = null;
  let onSelectCb = null;

  function ensureModal() {
    if (modalEl) return modalEl;
    const overlay = document.createElement('div');
    overlay.className = 'modal';
    overlay.id = 'quoteGalleryOverlay';
    overlay.style.display = 'none';
    overlay.innerHTML = `
      <div class="modal-content">
        <h3>Select Image</h3>
        <div class="gallery-filters">
          <input type="text" id="qgSearch" placeholder="Search name, tag, category...">
          <select id="qgTag"><option value="">All tags</option></select>
          <select id="qgCat"><option value="">All categories</option></select>
        </div>
        <div class="gallery-grid" id="qgGrid"></div>
        <div class="gallery-actions">
          <button id="qgClose" class="btn btn-secondary">Close</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    modalEl = overlay;

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.style.display = 'none';
    });
    overlay.querySelector('#qgClose').addEventListener('click', () => {
      overlay.style.display = 'none';
    });
    overlay.querySelector('#qgSearch').addEventListener('input', () => loadGrid());
    overlay.querySelector('#qgTag').addEventListener('change', () => loadGrid());
    overlay.querySelector('#qgCat').addEventListener('change', () => loadGrid());
    return overlay;
  }

  async function loadGrid() {
    const grid = modalEl.querySelector('#qgGrid');
    grid.innerHTML = '<p>Loading images...</p>';
    const q = modalEl.querySelector('#qgSearch').value || '';
    const tag = modalEl.querySelector('#qgTag').value || '';
    const cat = modalEl.querySelector('#qgCat').value || '';
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (tag) params.set('tag', tag);
    if (cat) params.set('category', cat);
    try {
      const res = await fetch('/quote_editor/images?' + params.toString());
      const data = await res.json();
      const images = data.images || [];

      const tagSel = modalEl.querySelector('#qgTag');
      const curTag = tagSel.value;
      tagSel.innerHTML = '<option value="">All tags</option>' + (data.tags || []).map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
      tagSel.value = curTag;
      const catSel = modalEl.querySelector('#qgCat');
      const curCat = catSel.value;
      catSel.innerHTML = '<option value="">All categories</option>' + (data.categories || []).map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
      catSel.value = curCat;

      if (!images.length) {
        grid.innerHTML = '<p>No images available. Upload some in the Quote Editor image library first.</p>';
        return;
      }
      grid.innerHTML = images.map(img => `
        <div class="gallery-item" data-url="${escapeHtml(img.url)}" data-filename="${escapeHtml(img.filename || '')}">
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.original_name || img.filename)}">
          <div class="gallery-item__name">${escapeHtml(img.original_name || img.filename)}</div>
        </div>`).join('');
      grid.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', () => {
          const url = item.dataset.url;
          const filename = item.dataset.filename;
          if (onSelectCb) onSelectCb({ url, filename });
          modalEl.style.display = 'none';
        });
      });
    } catch (err) {
      grid.innerHTML = '<p>Failed to load images.</p>';
    }
  }

  window.QuoteGallery = {
    open(onSelect) {
      onSelectCb = typeof onSelect === 'function' ? onSelect : null;
      const m = ensureModal();
      m.style.display = 'flex';
      loadGrid();
    }
  };
})();

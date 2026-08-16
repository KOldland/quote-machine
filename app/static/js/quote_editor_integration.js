(function () {
  'use strict';

  async function addCalcToQuote() {
    try {
      const res = await fetch('/quote_editor/add-calc-block');
      const data = await res.json();
      if (data.success) {
        const store = await fetch('/quote_editor/set-pending-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ block: data.block }),
        }).then(r => r.json());
        if (store.success) {
          window.location.href = '/quote_editor';
        }
      } else {
        alert('Failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Failed to add calculator to quote.');
    }
  }

  async function addImagesToQuote() {
    try {
      const res = await fetch('/quote_editor/add-image-group-block');
      const data = await res.json();
      if (data.success) {
        const store = await fetch('/quote_editor/set-pending-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ block: data.block }),
        }).then(r => r.json());
        if (store.success) {
          window.location.href = '/quote_editor';
        }
      } else {
        alert('Failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Failed to add images to quote.');
    }
  }

  async function saveDraft() {
    const name = prompt('Draft name:', 'Draft ' + new Date().toLocaleString());
    if (!name) return;
    try {
      const res = await fetch('/quote_editor/drafts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (data.success) {
        alert('Draft saved');
      } else {
        alert('Failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Failed to save draft');
    }
  }

  async function loadDraftsList() {
    const container = document.getElementById('draftsList');
    container.innerHTML = '<p>Loading...</p>';
    try {
      const res = await fetch('/quote_editor/drafts');
      const data = await res.json();
      const drafts = data.drafts || [];
      if (!drafts.length) {
        container.innerHTML = '<p>No saved drafts.</p>';
        return;
      }
      container.innerHTML = drafts.map(d => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #eee;">
          <div><strong>${escapeHtml(d.name)}</strong><br><small>${d.created_at}</small></div>
          <div>
            <button class="load-draft-btn" data-draft-id="${d.id}">Load</button>
            <button class="delete-draft-btn" data-draft-id="${d.id}" style="color:red; background:none; border:none; cursor:pointer;">Delete</button>
          </div>
        </div>
      `).join('');
      container.querySelectorAll('.load-draft-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const draftId = btn.dataset.draftId;
          const r = await fetch(`/quote_editor/drafts/${draftId}/load`, { method: 'POST' });
          const d = await r.json();
          if (d.success) {
            document.getElementById('draftModal').style.display = 'none';
            window.location.reload();
          } else {
            alert('Failed: ' + (d.error || 'unknown'));
          }
        });
      });
      container.querySelectorAll('.delete-draft-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const draftId = btn.dataset.draftId;
          if (!confirm('Delete this draft?')) return;
          await fetch(`/quote_editor/drafts/${draftId}`, { method: 'DELETE' });
          loadDraftsList();
        });
      });
    } catch (err) {
      container.innerHTML = '<p>Failed to load drafts.</p>';
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function init() {
    document.getElementById('addCalcToQuoteBtn')?.addEventListener('click', addCalcToQuote);
    document.getElementById('addImagesToQuoteBtn')?.addEventListener('click', addImagesToQuote);
    document.getElementById('saveDraftBtn')?.addEventListener('click', saveDraft);
    document.getElementById('loadDraftBtn')?.addEventListener('click', () => {
      document.getElementById('draftModal').style.display = 'flex';
      loadDraftsList();
    });
    document.getElementById('closeDraftModal')?.addEventListener('click', () => {
      document.getElementById('draftModal').style.display = 'none';
    });
    document.getElementById('draftModal')?.addEventListener('click', (e) => {
      if (e.target === document.getElementById('draftModal')) {
        document.getElementById('draftModal').style.display = 'none';
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
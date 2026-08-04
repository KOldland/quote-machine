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

  function init() {
    document.getElementById('addCalcToQuoteBtn')?.addEventListener('click', addCalcToQuote);
    document.getElementById('addImagesToQuoteBtn')?.addEventListener('click', addImagesToQuote);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
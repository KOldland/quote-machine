(function () {
  'use strict';

  async function addFormPageToQuote() {
    const pageKey = document.body.dataset.pageKey || new URLSearchParams(window.location.search).get('page');
    if (!pageKey) {
      alert('Unable to determine current page key.');
      return;
    }
    try {
      const res = await fetch(`/quote_editor/add-form-block?page=${encodeURIComponent(pageKey)}`);
      const data = await res.json();
      if (data.success) {
        sessionStorage.setItem('quote_editor_pending_blocks', JSON.stringify(data.blocks));
        window.location.href = '/quote_editor';
      } else {
        alert('Failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Failed to add page to quote.');
    }
  }

  async function addCalcToQuote() {
    try {
      const res = await fetch('/quote_editor/add-calc-block');
      const data = await res.json();
      if (data.success) {
        sessionStorage.setItem('quote_editor_pending_block', JSON.stringify(data.block));
        window.location.href = '/quote_editor';
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
        sessionStorage.setItem('quote_editor_pending_block', JSON.stringify(data.block));
        window.location.href = '/quote_editor';
      } else {
        alert('Failed: ' + (data.error || 'unknown'));
      }
    } catch (err) {
      alert('Failed to add images to quote.');
    }
  }

  function init() {
    document.getElementById('addFormToQuoteBtn')?.addEventListener('click', addFormPageToQuote);
    document.getElementById('addCalcToQuoteBtn')?.addEventListener('click', addCalcToQuote);
    document.getElementById('addImagesToQuoteBtn')?.addEventListener('click', addImagesToQuote);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

(function () {
  'use strict';

  const DB = window.CodeNovaOfflineDB;
  if (!DB) return;

  const SKIP_PATHS = new Set(['/login', '/logout', '/student/api/chat']);
  let syncing = false;

  function byId(id) { return document.getElementById(id); }

  function ensureStatusBar() {
    let bar = byId('offlineStatus');
    if (bar) return bar;
    bar = document.createElement('div');
    bar.id = 'offlineStatus';
    bar.className = 'offline-status';
    bar.setAttribute('role', 'status');
    document.body.appendChild(bar);
    return bar;
  }

  async function renderStatus(extra) {
    const bar = ensureStatusBar();
    const pending = await DB.count().catch(() => 0);
    const online = navigator.onLine;
    bar.classList.toggle('offline', !online);
    bar.classList.toggle('online', online);
    bar.innerHTML = online
      ? `<span>● Online</span>${pending ? `<span class="offline-pending">${pending} change${pending === 1 ? '' : 's'} waiting</span>` : '<span>✓ Synced</span>'}${extra ? `<span>${extra}</span>` : ''}`
      : `<span>● Offline</span><span class="offline-pending">Changes are saved on this device and will sync automatically.</span>`;
  }

  async function serializeForm(form) {
    const fields = [];
    const formData = new FormData(form);
    for (const [name, value] of formData.entries()) {
      if (typeof value === 'string') fields.push([name, value]);
    }
    return fields;
  }

  function canQueue(form) {
    if ((form.method || 'get').toLowerCase() !== 'post') return false;
    if (form.dataset.offline === 'false') return false;
    const action = new URL(form.action || window.location.href, window.location.href);
    if (action.origin !== window.location.origin) return false;
    return !SKIP_PATHS.has(action.pathname);
  }

  async function queueForm(form) {
    const action = new URL(form.action || window.location.href, window.location.href);
    const fields = await serializeForm(form);
    await DB.add({
      action: action.pathname + action.search,
      method: 'POST',
      fields,
      createdAt: new Date().toISOString()
    });
    await renderStatus('Saved locally');
  }

  async function replayItem(item) {
    const body = new URLSearchParams();
    for (const [name, value] of item.fields || []) body.append(name, value);
    const response = await fetch(item.action, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-Offline-Replay': '1'
      },
      body,
      redirect: 'follow'
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response;
  }

  async function syncOutbox() {
    if (syncing || !navigator.onLine) return;
    syncing = true;
    try {
      const items = await DB.all();
      for (const item of items) {
        try {
          await replayItem(item);
          await DB.remove(item.id);
        } catch (error) {
          console.warn('Offline sync paused:', item, error);
          break;
        }
      }
      if (items.length) {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_PAGE_CACHE' });
        }
        await renderStatus(items.length ? 'Sync checked' : '');
      } else {
        await renderStatus();
      }
    } finally {
      syncing = false;
    }
  }

  function registerHandlers() {
    document.addEventListener('submit', async (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement) || !canQueue(form)) return;
      if (navigator.onLine) return;
      event.preventDefault();
      try {
        await queueForm(form);
        form.reset();
        const note = document.createElement('div');
        note.className = 'offline-inline-note';
        note.textContent = 'Saved offline. It will be sent automatically when internet returns.';
        form.parentElement.appendChild(note);
      } catch (error) {
        console.error('Could not save form offline:', error);
        alert('This change could not be saved offline on this device.');
      }
    }, true);

    window.addEventListener('online', () => {
      renderStatus();
      setTimeout(syncOutbox, 250);
    });

    window.addEventListener('offline', () => renderStatus());

    document.addEventListener('click', async (event) => {
      const link = event.target.closest('a.logout');
      if (link && navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_OFFLINE_DATA' });
        await DB.clear().catch(() => {});
      }
    }, true);
  }

  async function boot() {
    registerHandlers();
    await renderStatus();
    if (navigator.onLine) await syncOutbox();
  }

  boot();
  window.CodeNovaSync = { syncOutbox, renderStatus };
})();

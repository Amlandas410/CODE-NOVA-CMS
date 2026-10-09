const SHELL_CACHE = 'code-nova-shell-v2';
const PAGE_CACHE = 'code-nova-pages-v1';
const STATIC_ASSETS = [
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/js/offline-db.js',
  '/static/js/offline.js',
  '/static/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(Promise.all([
    self.clients.claim(),
    caches.keys().then(names => Promise.all(
      names
        .filter(name => name.startsWith('code-nova-shell-') && name !== SHELL_CACHE)
        .map(name => caches.delete(name))
    ))
  ]));
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'CLEAR_PAGE_CACHE') {
    event.waitUntil(caches.delete(PAGE_CACHE));
  }
  if (event.data?.type === 'CLEAR_ALL_OFFLINE_DATA') {
    event.waitUntil(Promise.all([caches.delete(PAGE_CACHE), caches.delete(SHELL_CACHE)]));
  }
});

async function pageRequest(request) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok && !response.redirected) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function staticAssetRequest(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === '/logout') return;

  if (request.mode === 'navigate') {
    event.respondWith(pageRequest(request));
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(staticAssetRequest(request));
  }
});

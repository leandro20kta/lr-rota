/* LR Rota — service worker: app shell em cache, resto pela rede */
const CACHE = 'lr-rota-v23';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icons/car.png', './icons/icon-192.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if(e.request.method !== 'GET') return;
  // app shell: network first, cache fallback (so updates arrive, offline still opens)
  if(url.origin === location.origin){
    e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request).then(r => r || caches.match('./index.html'))));
    return;
  }
  // map tiles and libraries: cache first, limited
  if(/tile\.openstreetmap\.org|unpkg\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host)){
    e.respondWith(caches.open('lr-tiles').then(async c => { const hit = await c.match(e.request); if(hit) return hit; const r = await fetch(e.request); if(r.ok) c.put(e.request, r.clone()); return r; }).catch(() => fetch(e.request)));
  }
});

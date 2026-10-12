/* Offline support for Mark Sync. Caches only the app itself and its libraries;
   slides and recordings live in IndexedDB and never pass through here. */
const CACHE='mark-sync-v1';
const SHELL=['mark-sync.html','mark-sync.webmanifest','mark-sync-icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'];
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.allSettled(SHELL.map(u=>c.add(u)))).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('mark-sync-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET'||req.url.startsWith('blob:')) return;
  const url=new URL(req.url);
  if(url.origin===location.origin){
    // App files: network first so updates arrive, cached copy when offline.
    e.respondWith(fetch(req).then(r=>{ if(r.ok){ const c=r.clone(); caches.open(CACHE).then(k=>k.put(req,c)); } return r; })
      .catch(()=>caches.match(req,{ignoreSearch:true}).then(r=>r||caches.match('mark-sync.html'))));
  } else if(/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host)){
    // Versioned libraries and fonts: cache first.
    e.respondWith(caches.match(req).then(r=>r||fetch(req).then(n=>{ const c=n.clone(); caches.open(CACHE).then(k=>k.put(req,c)); return n; })));
  }
});

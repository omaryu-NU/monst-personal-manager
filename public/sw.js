const CACHE='monst-personal-shell-v10';
const SHELL=['/','/icon.svg','/manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('monst-personal-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting()});
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/__/')||url.pathname.startsWith('/api/')||req.headers.has('authorization'))return;
 // Network-first navigation, cached assets only. No Firestore/Auth tokens are stored by this worker.
 if(req.mode==='navigate'){event.respondWith(fetch(req).then(r=>{if(r.ok){const copy=r.clone();event.waitUntil(caches.open(CACHE).then(c=>c.put('/',copy)))}return r}).catch(()=>caches.match('/')));return;}
 if(!['script','style','font','image','manifest'].includes(req.destination))return;
 event.respondWith(caches.match(req).then(cached=>cached||fetch(req).then(r=>{if(r.ok){const copy=r.clone();event.waitUntil(caches.open(CACHE).then(async c=>{await c.put(req,copy);const keys=await c.keys();if(keys.length>120)await c.delete(keys[0]);}))}return r})));
});

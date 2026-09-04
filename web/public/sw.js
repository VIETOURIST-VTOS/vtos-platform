// Service worker tối giản: cho phép cài đặt PWA; cache vỏ ứng dụng, API luôn lấy mạng.
const CACHE = "vtos-shell-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then((r) => { const c = r.clone(); caches.open(CACHE).then((cache) => cache.put(e.request, c)); return r; })
    .catch(() => caches.match(e.request)));
});

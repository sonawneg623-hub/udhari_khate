/* उधारी खाते – Service Worker
 * - अ‍ॅपचे शेल (CSS/JS/आयकॉन/फॉन्ट) कॅश होते -> अ‍ॅप वेगाने उघडते
 * - ग्राहकांचा डेटा / HTML पाने कधीही कॅश होत नाहीत (खाजगी माहिती फोनवर साठू नये म्हणून)
 * - इंटरनेट नसल्यास "इंटरनेट नाही" पान दिसते
 */
const VERSION = "v3";
const STATIC_CACHE = "udhari-static-" + VERSION;
const FONT_CACHE = "udhari-fonts-" + VERSION;
const PRECACHE = [
  "/offline",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((c) => c.addAll(PRECACHE.map((u) => new Request(u, { cache: "reload" }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k.startsWith("udhari-") && k !== STATIC_CACHE && k !== FONT_CACHE)
            .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

function staleWhileRevalidate(request, cacheName) {
  return caches.open(cacheName).then((cache) =>
    cache.match(request, { ignoreSearch: false }).then((hit) => {
      const net = fetch(request).then((res) => {
        if (res && (res.ok || res.type === "opaque")) cache.put(request, res.clone());
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // पान उघडणे: नेहमी सर्व्हरकडून; ऑफलाइन असल्यास ऑफलाइन पान
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match("/offline")));
    return;
  }

  // फॉन्ट
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    event.respondWith(staleWhileRevalidate(req, FONT_CACHE));
    return;
  }

  // स्वतःचे static फाइल्स
  if (url.origin === self.location.origin && url.pathname.startsWith("/static/")) {
    event.respondWith(staleWhileRevalidate(req, STATIC_CACHE));
  }
  // बाकी सर्व (डेटा) -> थेट नेटवर्क
});

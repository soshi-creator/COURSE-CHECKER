const CACHE_NAME = "kuccps-cache-v1.1";
const urlsToCache = [
  "/",
  "/offline.html",
  "/static/alreadypaid.css",
  "/static/certificate.css",
  "/static/diploma.css",
  "/static/kmtc.css",
  "/static/input.css",
  "/static/payment.css",
  "/static/style.css",
  "/static/navbar.css",
  "/static/paidresults.css",
  "/static/bootstrap.min.css",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png",
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css",
  "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
];

// Install event - cache essential files
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Cache opened");
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log("Deleting old cache:", cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => {
      console.log("Service worker activated");
      return self.clients.claim();
    })
  );
});

// Enhanced fetch event
self.addEventListener("fetch", (event) => {
  // Skip non-GET requests
  if (event.request.method !== "GET") return;
  
  // Skip external URLs that shouldn't be cached
  const url = new URL(event.request.url);
  if (url.hostname !== self.location.hostname && 
      !url.href.includes('bootstrap-icons') &&
      !url.href.includes('fonts.googleapis.com')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      // Return cached response if available
      if (cachedResponse) {
        // Update cache in background
        fetchAndCache(event.request);
        return cachedResponse;
      }

      // Try network request
      return fetch(event.request)
        .then((networkResponse) => {
          // Cache successful responses
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Network failed - show offline page for HTML requests
          if (event.request.headers.get("Accept").includes("text/html")) {
            return caches.match("/offline.html");
          }
          
          // Return fallback for other file types
          return new Response("Offline - Content not available", {
            status: 503,
            statusText: "Service Unavailable",
            headers: { "Content-Type": "text/plain" }
          });
        });
    })
  );
});

// Helper function to fetch and cache in background
function fetchAndCache(request) {
  fetch(request).then((response) => {
    if (response && response.status === 200) {
      const responseToCache = response.clone();
      caches.open(CACHE_NAME).then((cache) => {
        cache.put(request, responseToCache);
      });
    }
  }).catch(() => {
    // Silently fail - we're just updating cache
  });
}

// Background sync for failed requests (when back online)
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-forms") {
    event.waitUntil(syncFormData());
  }
});

async function syncFormData() {
  // Implement data sync when back online
  console.log("Background sync started");
  // You can store form submissions in IndexedDB and sync here
}

self.addEventListener("push", (event) => {
  let data = { title: "KUCCPS Course Checker", body: "New update", url: "/" };
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: "/static/icons/icon-192x192.png",
    badge: "/static/icons/icon-192x192.png",
    vibrate: [200, 100, 200],
    data: data.url
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});


lf.addEventListener("notificationclick", function(event) {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(url));
});

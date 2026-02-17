/**
 * Service Worker for Restaurant Manager PWA
 *
 * Strategies:
 *   - Cache-first for static assets (CSS, JS, icons, fonts)
 *   - Network-first for API calls and page navigations
 *   - Offline fallback page when network is unavailable
 */

const CACHE_NAME = 'restaurant-manager-v1';

/** Static assets to pre-cache during installation. */
const PRECACHE_URLS = [
  '/',
  '/tables',
  '/menu',
  '/orders',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

/**
 * Offline fallback HTML served when both network and cache miss on a
 * navigation request.
 */
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline - Restaurant Manager</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f5f6fa;
      color: #2c3e50;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      text-align: center;
      padding: 2rem;
    }
    .offline-container { max-width: 420px; }
    .offline-icon {
      font-size: 4rem;
      margin-bottom: 1.5rem;
      opacity: 0.6;
    }
    h1 { font-size: 1.6rem; margin-bottom: 0.75rem; }
    p { color: #95a5a6; line-height: 1.6; margin-bottom: 1.5rem; }
    button {
      padding: 0.7rem 2rem;
      background: #FF6B35;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 1rem;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    button:hover { opacity: 0.85; }
  </style>
</head>
<body>
  <div class="offline-container">
    <div class="offline-icon">&#x1F50C;</div>
    <h1>You're Offline</h1>
    <p>
      It looks like you've lost your internet connection.
      Some features may be unavailable until you reconnect.
    </p>
    <button onclick="window.location.reload()">Try Again</button>
  </div>
</body>
</html>`;

/* ==========================================================================
   Install Event — pre-cache core assets
   ========================================================================== */

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        // Use addAll with individual fallbacks so one 404 does not block install.
        return Promise.allSettled(
          PRECACHE_URLS.map((url) =>
            cache.add(url).catch((err) => {
              console.warn(`[SW] Failed to pre-cache: ${url}`, err);
            })
          )
        );
      })
      .then(() => {
        // Immediately activate without waiting for open tabs to close.
        return self.skipWaiting();
      })
  );
});

/* ==========================================================================
   Activate Event — clean up old caches
   ========================================================================== */

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => {
              console.log(`[SW] Deleting old cache: ${name}`);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        // Take control of all open clients immediately.
        return self.clients.claim();
      })
  );
});

/* ==========================================================================
   Fetch Event — routing strategies
   ========================================================================== */

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle requests from our own origin.
  if (url.origin !== self.location.origin) {
    return;
  }

  // --- API calls: network-first with cache fallback ---
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // --- Static assets: cache-first with network fallback ---
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // --- Navigation (HTML pages): network-first with offline fallback ---
  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  // --- Default: network-first ---
  event.respondWith(networkFirst(request));
});

/* ==========================================================================
   Strategy Helpers
   ========================================================================== */

/**
 * Determine whether a URL path points to a static asset that benefits from
 * cache-first loading.
 */
function isStaticAsset(pathname) {
  return /\.(?:css|js|png|jpg|jpeg|gif|svg|ico|woff2?|ttf|eot)$/.test(pathname);
}

/**
 * Cache-first strategy.
 * Return the cached response if available; otherwise fetch from the network,
 * cache the result, and return it.
 */
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // If both cache and network fail, return a basic error response.
    return new Response('Offline — asset unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

/**
 * Network-first strategy.
 * Try the network; on success, update the cache. On failure fall back to
 * the cached version.
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);

    // Only cache GET requests.
    if (request.method === 'GET' && networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return a JSON error for API-like requests.
    return new Response(
      JSON.stringify({ error: 'You are offline and no cached data is available.' }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Network-first strategy with an offline HTML fallback for navigation requests.
 */
async function networkFirstNavigation(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Try to serve the cached version of the page.
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Serve the inline offline fallback page.
    return new Response(OFFLINE_HTML, {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/html' },
    });
  }
}

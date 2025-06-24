/**
 * Football Manager Service Worker - 2025 Edition
 * Provides offline functionality and caching for PWA
 */

const CACHE_NAME = 'football-manager-v2025.1';
const STATIC_CACHE_NAME = 'football-manager-static-v2025.1';
const DYNAMIC_CACHE_NAME = 'football-manager-dynamic-v2025.1';

// Static assets to cache
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/manifest.json',
    '/health',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdn.socket.io/4.7.4/socket.io.min.js'
];

// Routes that should always try network first
const NETWORK_FIRST_ROUTES = [
    '/api/',
    '/admin/',
    '/auth/'
];

// Routes that can be cached
const CACHE_FIRST_ROUTES = [
    '/static/',
    'https://cdn.jsdelivr.net/',
    'https://fonts.googleapis.com/',
    'https://fonts.gstatic.com/'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE_NAME).then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            }),
            self.skipWaiting() // Activate new service worker immediately
        ])
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE_NAME && 
                            cacheName !== DYNAMIC_CACHE_NAME &&
                            cacheName.startsWith('football-manager-')) {
                            console.log('Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            self.clients.claim() // Take control of all clients
        ])
    );
});

// Fetch event - handle all network requests
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-HTTP requests
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // Determine caching strategy based on the request
    if (isNetworkFirstRoute(url.pathname)) {
        event.respondWith(networkFirstStrategy(request));
    } else if (isCacheFirstRoute(url.href)) {
        event.respondWith(cacheFirstStrategy(request));
    } else {
        event.respondWith(staleWhileRevalidateStrategy(request));
    }
});

// Network first strategy (for API calls, dynamic content)
async function networkFirstStrategy(request) {
    const dynamicCache = await caches.open(DYNAMIC_CACHE_NAME);
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful responses
            await dynamicCache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache for:', request.url);
        
        const cachedResponse = await dynamicCache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline fallback for specific routes
        if (request.url.includes('/admin/') || request.url.includes('/tournaments/')) {
            return createOfflineFallback(request);
        }
        
        throw error;
    }
}

// Cache first strategy (for static assets, CDN resources)
async function cacheFirstStrategy(request) {
    const staticCache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await staticCache.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            await staticCache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Cache first failed for:', request.url);
        throw error;
    }
}

// Stale while revalidate strategy (for pages)
async function staleWhileRevalidateStrategy(request) {
    const dynamicCache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await dynamicCache.match(request);
    
    // Start the network request regardless of cache status
    const networkPromise = fetch(request).then(response => {
        if (response.ok) {
            dynamicCache.put(request, response.clone());
        }
        return response;
    }).catch(error => {
        console.log('Service Worker: Network error in stale-while-revalidate:', error);
        return null;
    });
    
    // Return cached version immediately if available, otherwise wait for network
    return cachedResponse || networkPromise;
}

// Helper functions
function isNetworkFirstRoute(pathname) {
    return NETWORK_FIRST_ROUTES.some(route => pathname.startsWith(route));
}

function isCacheFirstRoute(url) {
    return CACHE_FIRST_ROUTES.some(route => url.startsWith(route));
}

// Create offline fallback page
function createOfflineFallback(request) {
    return new Response(`
        <!DOCTYPE html>
        <html lang="en" data-theme="auto">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - Football Manager</title>
            <style>
                :root {
                    --primary-color: #4f46e5;
                    --background-primary: #ffffff;
                    --text-primary: #0f172a;
                    --text-secondary: #64748b;
                }
                
                @media (prefers-color-scheme: dark) {
                    :root {
                        --background-primary: #0f172a;
                        --text-primary: #f8fafc;
                        --text-secondary: #cbd5e1;
                    }
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background-color: var(--background-primary);
                    color: var(--text-primary);
                    margin: 0;
                    padding: 2rem;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    text-align: center;
                }
                
                .offline-icon {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                    color: var(--primary-color);
                }
                
                h1 {
                    margin-bottom: 0.5rem;
                    color: var(--text-primary);
                }
                
                p {
                    color: var(--text-secondary);
                    max-width: 400px;
                    line-height: 1.6;
                }
                
                .retry-btn {
                    background-color: var(--primary-color);
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    font-weight: 500;
                    cursor: pointer;
                    margin-top: 1rem;
                }
                
                .retry-btn:hover {
                    opacity: 0.9;
                }
            </style>
        </head>
        <body>
            <div class="offline-icon">📱</div>
            <h1>You're Offline</h1>
            <p>It looks like you've lost your internet connection. Please check your network and try again.</p>
            <button class="retry-btn" onclick="window.location.reload()">Try Again</button>
            
            <script>
                // Auto-retry when online
                window.addEventListener('online', () => {
                    window.location.reload();
                });
            </script>
        </body>
        </html>
    `, {
        status: 200,
        statusText: 'OK',
        headers: { 'Content-Type': 'text/html' }
    });
}

// Background sync for when connection is restored
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('Service Worker: Background sync triggered');
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Handle any pending operations when connection is restored
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'BACKGROUND_SYNC',
            message: 'Connection restored, syncing data...'
        });
    });
}

// Push notifications
self.addEventListener('push', event => {
    if (!event.data) {
        return;
    }
    
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/favicon-192x192.png',
        badge: '/static/favicon-96x96.png',
        tag: data.tag || 'general',
        requireInteraction: data.requireInteraction || false,
        actions: data.actions || [],
        data: data.data || {}
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    const url = event.notification.data.url || '/';
    
    event.waitUntil(
        clients.openWindow(url)
    );
});

// Message handler for communication with main thread
self.addEventListener('message', event => {
    const { type, data } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
        case 'GET_VERSION':
            event.ports[0].postMessage({ version: CACHE_NAME });
            break;
        case 'CLEAR_CACHE':
            clearAllCaches().then(() => {
                event.ports[0].postMessage({ success: true });
            });
            break;
    }
});

// Clear all caches
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    return Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
}

console.log('Service Worker: Loaded', CACHE_NAME);
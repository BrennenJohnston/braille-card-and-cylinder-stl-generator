/**
 * Service Worker - Advanced Caching and Offline Support
 * Optimized for Braille STL Generator on Cloudflare Pages
 */

const CACHE_NAME = 'braille-stl-v2.0.0';
const STATIC_CACHE_NAME = 'braille-static-v2.0.0';
const DYNAMIC_CACHE_NAME = 'braille-dynamic-v2.0.0';

// Assets to cache immediately on install
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/main.js',
  '/main.css', // Will be generated with hash
  '/liblouis/build-no-tables-utf16.js',
  '/liblouis/easy-api.js'
];

// Critical braille tables to cache
const CRITICAL_BRAILLE_TABLES = [
  '/liblouis/tables/en-us-g1.ctb',
  '/liblouis/tables/en-us-g2.ctb',
  '/liblouis/tables/en-gb-g1.utb',
  '/liblouis/tables/UEBC-g1.utb',
  '/liblouis/tables/UEBC-g2.ctb'
];

// Large assets to cache on demand
const LARGE_ASSETS = [
  '/geometry-worker.js',
  '/liblouis-worker.js',
  '/chunks/three-*.js',
  '/chunks/three-bvh-csg-*.js'
];

console.log('🔧 Service Worker loading...');

// Install event - cache core assets
self.addEventListener('install', (event) => {
  console.log('📦 Service Worker installing...');
  
  event.waitUntil(
    Promise.all([
      // Cache core application assets
      caches.open(STATIC_CACHE_NAME).then(cache => {
        console.log('📚 Caching core assets...');
        return cache.addAll(CORE_ASSETS.concat(CRITICAL_BRAILLE_TABLES));
      }),
      
      // Preload critical resources
      preloadCriticalResources()
    ]).then(() => {
      console.log('✅ Service Worker installed successfully');
      self.skipWaiting(); // Activate immediately
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // Delete old cache versions
          if (cacheName !== STATIC_CACHE_NAME && 
              cacheName !== DYNAMIC_CACHE_NAME &&
              cacheName.startsWith('braille-')) {
            console.log(`🗑️ Deleting old cache: ${cacheName}`);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ Service Worker activated');
      return self.clients.claim(); // Take control of all pages
    })
  );
});

// Fetch event - intelligent caching strategy
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip external domains
  if (url.origin !== self.location.origin) {
    return;
  }
  
  event.respondWith(handleRequest(request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  
  try {
    // Strategy 1: Core assets - Cache First
    if (isCoreAsset(pathname)) {
      return await cacheFirst(request, STATIC_CACHE_NAME);
    }
    
    // Strategy 2: Large assets (workers, chunks) - Cache First with network fallback
    if (isLargeAsset(pathname)) {
      return await cacheFirst(request, STATIC_CACHE_NAME);
    }
    
    // Strategy 3: Braille tables - Cache First (they rarely change)
    if (pathname.includes('/liblouis/tables/')) {
      return await cacheFirst(request, STATIC_CACHE_NAME);
    }
    
    // Strategy 4: HTML - Network First with cache fallback (for updates)
    if (pathname.endsWith('.html') || pathname === '/') {
      return await networkFirst(request, DYNAMIC_CACHE_NAME);
    }
    
    // Strategy 5: Generated STL files - Don't cache (they're unique)
    if (pathname.endsWith('.stl')) {
      return fetch(request);
    }
    
    // Strategy 6: Everything else - Stale While Revalidate
    return await staleWhileRevalidate(request, DYNAMIC_CACHE_NAME);
    
  } catch (error) {
    console.error('Service Worker fetch error:', error);
    
    // Fallback to network
    try {
      return await fetch(request);
    } catch (networkError) {
      // Return offline page if available
      if (pathname === '/' || pathname.endsWith('.html')) {
        const cache = await caches.open(STATIC_CACHE_NAME);
        const cachedResponse = await cache.match('/index.html');
        if (cachedResponse) {
          return cachedResponse;
        }
      }
      
      // Generic offline response
      return new Response('Offline - Please check your connection', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'text/plain' }
      });
    }
  }
}

// Caching strategies
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Return cached version and update in background
    fetch(request).then(response => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
    }).catch(() => {}); // Ignore background update failures
    
    return cachedResponse;
  }
  
  // Not in cache, fetch and cache
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    throw error;
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Network failed, try cache
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  // Always try to update from network in background
  const networkPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => {}); // Ignore update failures
  
  // Return cached version immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // No cached version, wait for network
  return await networkPromise;
}

// Helper functions
function isCoreAsset(pathname) {
  return CORE_ASSETS.some(asset => pathname === asset || pathname.endsWith(asset));
}

function isLargeAsset(pathname) {
  return pathname.includes('worker.js') || 
         pathname.includes('/chunks/') ||
         pathname.includes('three-') ||
         pathname.endsWith('.wasm');
}

// Preload critical resources
async function preloadCriticalResources() {
  // Preload essential braille tables
  const cache = await caches.open(STATIC_CACHE_NAME);
  
  const preloadPromises = CRITICAL_BRAILLE_TABLES.map(async (table) => {
    try {
      const response = await fetch(table);
      if (response.ok) {
        await cache.put(table, response);
        console.log(`✅ Preloaded: ${table}`);
      }
    } catch (error) {
      console.warn(`⚠️ Failed to preload: ${table}`);
    }
  });
  
  await Promise.allSettled(preloadPromises);
}

// Message handling for cache management
self.addEventListener('message', (event) => {
  if (event.data && event.data.type) {
    switch (event.data.type) {
      case 'SKIP_WAITING':
        self.skipWaiting();
        break;
        
      case 'CLEAR_CACHE':
        clearAllCaches().then(() => {
          event.ports[0].postMessage({ success: true });
        });
        break;
        
      case 'CACHE_STATS':
        getCacheStats().then(stats => {
          event.ports[0].postMessage(stats);
        });
        break;
        
      case 'PRELOAD_LARGE_ASSETS':
        preloadLargeAssets().then(() => {
          event.ports[0].postMessage({ success: true });
        });
        break;
    }
  }
});

async function clearAllCaches() {
  console.log('🗑️ Clearing all caches...');
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames.map(cacheName => caches.delete(cacheName))
  );
  console.log('✅ All caches cleared');
}

async function getCacheStats() {
  const cacheNames = await caches.keys();
  const stats = {};
  
  for (const cacheName of cacheNames) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    stats[cacheName] = {
      entries: keys.length,
      urls: keys.map(request => request.url)
    };
  }
  
  return stats;
}

async function preloadLargeAssets() {
  console.log('📦 Preloading large assets...');
  const cache = await caches.open(STATIC_CACHE_NAME);
  
  // Find and cache worker files
  try {
    const workerAssets = [
      '/geometry-worker.js',
      '/liblouis-worker.js'
    ];
    
    for (const asset of workerAssets) {
      try {
        const response = await fetch(asset);
        if (response.ok) {
          await cache.put(asset, response);
          console.log(`✅ Cached large asset: ${asset}`);
        }
      } catch (error) {
        console.warn(`⚠️ Failed to cache: ${asset}`);
      }
    }
  } catch (error) {
    console.warn('⚠️ Large asset preloading failed:', error);
  }
}

// Performance monitoring integration
self.addEventListener('fetch', (event) => {
  const start = performance.now();
  
  event.waitUntil(
    event.response.then(() => {
      const duration = performance.now() - start;
      
      // Log slow requests
      if (duration > 1000) {
        console.warn(`🐌 Slow request: ${event.request.url} (${duration.toFixed(1)}ms)`);
      }
    })
  );
});

console.log('✅ Service Worker loaded and ready');

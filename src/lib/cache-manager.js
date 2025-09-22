/**
 * Advanced Cache Manager - Intelligent caching for performance optimization
 * Works with Service Worker and IndexedDB for optimal performance
 */

import { openDB } from 'idb';

export class CacheManager {
  constructor() {
    this.dbPromise = this.safeInitDB();
    this.serviceWorker = null;
    this.memoryCache = new Map();
    this.maxMemoryCacheSize = 50; // Maximum items in memory cache
    
    console.log('💾 Cache Manager initializing...');
    this.initServiceWorker();
  }

  safeInitDB() {
    // In Node/test environments, indexedDB may not exist
    if (typeof indexedDB === 'undefined') {
      console.warn('⚠️ IndexedDB not available; falling back to in-memory cache for tests');
      // Provide a minimal stub with the APIs we use so code paths continue to work
      return Promise.resolve({
        transaction() {
          return {
            store: {
              put: async () => {},
              clear: async () => {},
              getAll: async () => [],
              get: async () => null,
              index() {
                return {
                  getAllKeys: async () => [],
                  get: async () => null
                };
              }
            },
            done: Promise.resolve()
          };
        }
      });
    }
    return this.initDB();
  }

  async initDB() {
    return openDB('BrailleSTLCache', 2, {
      upgrade(db, oldVersion, newVersion) {
        console.log(`📊 Upgrading database from ${oldVersion} to ${newVersion}`);
        
        // STL files cache
        if (!db.objectStoreNames.contains('stl-files')) {
          const store = db.createObjectStore('stl-files', { 
            keyPath: 'id' 
          });
          store.createIndex('hash', 'hash', { unique: true });
          store.createIndex('timestamp', 'timestamp');
          store.createIndex('size', 'size');
          store.createIndex('shapeType', 'shapeType');
        }
        
        // Braille translations cache
        if (!db.objectStoreNames.contains('braille-translations')) {
          const store = db.createObjectStore('braille-translations', {
            keyPath: 'id'
          });
          store.createIndex('textHash', 'textHash', { unique: true });
          store.createIndex('table', 'table');
          store.createIndex('timestamp', 'timestamp');
        }
        
        // Performance metrics cache
        if (!db.objectStoreNames.contains('performance-metrics')) {
          const store = db.createObjectStore('performance-metrics', {
            keyPath: 'id'
          });
          store.createIndex('timestamp', 'timestamp');
          store.createIndex('metric', 'metric');
        }
        
        // User preferences
        if (!db.objectStoreNames.contains('user-preferences')) {
          const store = db.createObjectStore('user-preferences', {
            keyPath: 'key'
          });
        }
      }
    });
  }

  async initServiceWorker() {
    if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        this.serviceWorker = registration;
        
        // Listen for service worker messages
        navigator.serviceWorker.addEventListener('message', (event) => {
          this.handleServiceWorkerMessage(event.data);
        });
        
        console.log('🔧 Service Worker registered successfully');
        
        // Preload large assets after initial load
        setTimeout(() => {
          this.preloadLargeAssets();
        }, 2000);
        
      } catch (error) {
        console.warn('⚠️ Service Worker registration failed:', error);
      }
    }
  }

  async preloadLargeAssets() {
    if (this.serviceWorker) {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          console.log('✅ Large assets preloaded successfully');
        }
      };
      
      this.serviceWorker.active?.postMessage(
        { type: 'PRELOAD_LARGE_ASSETS' },
        [messageChannel.port2]
      );
    }
  }

  generateHash(data) {
    // Simple hash function for cache keys
    let hash = 0;
    const str = typeof data === 'string' ? data : JSON.stringify(data);
    
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    
    return Math.abs(hash).toString(36);
  }

  async cacheSTL(textInput, brailleLines, settings, stlBuffer, stats) {
    try {
      const hash = this.generateHash({ textInput, brailleLines, settings });
      const id = `stl_${hash}_${Date.now()}`;
      
      const cacheEntry = {
        id,
        hash,
        textInput,
        brailleLines,
        settings,
        stlBuffer,
        stats,
        timestamp: Date.now(),
        size: stlBuffer.byteLength,
        shapeType: settings.shape_type || 'card'
      };
      
      const db = await this.dbPromise;
      const tx = db.transaction('stl-files', 'readwrite');
      
      await tx.store.put(cacheEntry);
      await tx.done;
      
      // Add to memory cache for immediate access
      this.memoryCache.set(hash, cacheEntry);
      this.trimMemoryCache();
      
      console.log(`💾 STL cached: ${hash} (${(stlBuffer.byteLength / 1024).toFixed(1)} KB)`);
      
      // Clean old entries
      await this.cleanOldSTLs();
      
      return hash;
    } catch (error) {
      console.error('❌ Failed to cache STL:', error);
      return null;
    }
  }

  async getCachedSTL(textInput, brailleLines, settings) {
    try {
      const hash = this.generateHash({ textInput, brailleLines, settings });
      
      // Check memory cache first
      if (this.memoryCache.has(hash)) {
        console.log(`⚡ STL found in memory cache: ${hash}`);
        return this.memoryCache.get(hash);
      }
      
      // Check IndexedDB
      const db = await this.dbPromise;
      const tx = db.transaction('stl-files', 'readonly');
      const index = tx.store.index('hash');
      const result = await index.get(hash);
      
      if (result) {
        // Add to memory cache for next time
        this.memoryCache.set(hash, result);
        this.trimMemoryCache();
        
        console.log(`💾 STL found in database cache: ${hash}`);
        return result;
      }
      
      return null;
    } catch (error) {
      console.error('❌ Failed to retrieve cached STL:', error);
      return null;
    }
  }

  async cacheBrailleTranslation(text, table, brailleResult) {
    try {
      const textHash = this.generateHash({ text, table });
      const id = `braille_${textHash}_${Date.now()}`;
      
      const cacheEntry = {
        id,
        textHash,
        originalText: text,
        table,
        brailleResult,
        timestamp: Date.now()
      };
      
      const db = await this.dbPromise;
      const tx = db.transaction('braille-translations', 'readwrite');
      
      await tx.store.put(cacheEntry);
      await tx.done;
      
      console.log(`🔤 Braille translation cached: ${table}`);
      
    } catch (error) {
      console.error('❌ Failed to cache braille translation:', error);
    }
  }

  async getCachedBrailleTranslation(text, table) {
    try {
      const textHash = this.generateHash({ text, table });
      
      const db = await this.dbPromise;
      const tx = db.transaction('braille-translations', 'readonly');
      const index = tx.store.index('textHash');
      const result = await index.get(textHash);
      
      if (result) {
        // Check if translation is recent (within 24 hours)
        const age = Date.now() - result.timestamp;
        if (age < 24 * 60 * 60 * 1000) {
          console.log(`🔤 Braille translation found in cache: ${table}`);
          return result.brailleResult;
        }
      }
      
      return null;
    } catch (error) {
      console.error('❌ Failed to retrieve cached braille translation:', error);
      return null;
    }
  }

  trimMemoryCache() {
    if (this.memoryCache.size > this.maxMemoryCacheSize) {
      // Remove oldest entries
      const entries = Array.from(this.memoryCache.entries());
      entries.sort((a, b) => (a[1].timestamp || 0) - (b[1].timestamp || 0));
      
      const toRemove = entries.slice(0, entries.length - this.maxMemoryCacheSize);
      toRemove.forEach(([key]) => this.memoryCache.delete(key));
      
      console.log(`🧹 Memory cache trimmed: removed ${toRemove.length} entries`);
    }
  }

  async cleanOldSTLs() {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('stl-files', 'readwrite');
      const index = tx.store.index('timestamp');
      
      // Keep only last 100 STL files
      const allKeys = await index.getAllKeys();
      if (allKeys.length > 100) {
        const keysToDelete = allKeys.slice(0, allKeys.length - 100);
        
        for (const key of keysToDelete) {
          const record = await index.get(key);
          if (record) {
            await tx.store.delete(record.id);
          }
        }
      }
      
      await tx.done;
      console.log('🧹 Old STL cache entries cleaned');
      
    } catch (error) {
      console.error('❌ Failed to clean old STLs:', error);
    }
  }

  async getCacheStats() {
    try {
      const db = await this.dbPromise;
      
      // Get STL file stats
      const stlTx = db.transaction('stl-files', 'readonly');
      const stlFiles = await stlTx.store.getAll();
      
      // Get braille translation stats
      const brailleTx = db.transaction('braille-translations', 'readonly');
      const brailleTranslations = await brailleTx.store.getAll();
      
      const totalSTLSize = stlFiles.reduce((sum, file) => sum + (file.size || 0), 0);
      
      const stats = {
        stlFiles: {
          count: stlFiles.length,
          totalSize: totalSize,
          totalSizeMB: (totalSTLSize / 1024 / 1024).toFixed(1),
          averageSize: stlFiles.length > 0 ? (totalSTLSize / stlFiles.length / 1024).toFixed(1) : 0
        },
        brailleTranslations: {
          count: brailleTranslations.length
        },
        memoryCache: {
          entries: this.memoryCache.size,
          maxSize: this.maxMemoryCacheSize
        },
        serviceWorker: {
          active: !!this.serviceWorker,
          scope: this.serviceWorker?.scope || 'none'
        }
      };
      
      return stats;
    } catch (error) {
      console.error('❌ Failed to get cache stats:', error);
      return null;
    }
  }

  async saveUserPreference(key, value) {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('user-preferences', 'readwrite');
      
      await tx.store.put({ key, value, timestamp: Date.now() });
      await tx.done;
      
      console.log(`💾 User preference saved: ${key}`);
    } catch (error) {
      console.error('❌ Failed to save user preference:', error);
    }
  }

  async getUserPreference(key, defaultValue = null) {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('user-preferences', 'readonly');
      const result = await tx.store.get(key);
      
      return result ? result.value : defaultValue;
    } catch (error) {
      console.error('❌ Failed to get user preference:', error);
      return defaultValue;
    }
  }

  handleServiceWorkerMessage(data) {
    switch (data.type) {
      case 'CACHE_UPDATED':
        console.log('🔄 Service Worker cache updated');
        break;
        
      case 'OFFLINE_READY':
        console.log('📱 Offline functionality ready');
        this.dispatchEvent(new CustomEvent('offline-ready'));
        break;
    }
  }

  async forceUpdate() {
    if (this.serviceWorker) {
      // Clear caches and force update
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        console.log('🔄 Force update completed');
        window.location.reload();
      };
      
      this.serviceWorker.active?.postMessage(
        { type: 'CLEAR_CACHE' },
        [messageChannel.port2]
      );
    }
  }

  // Predictive caching based on user behavior
  async enablePredictiveCaching() {
    console.log('🔮 Enabling predictive caching...');
    
    // Cache commonly used braille tables
    const commonTables = [
      'en-us-g1.ctb',
      'en-us-g2.ctb', 
      'en-ueb-g1.ctb'
    ];
    
    // Preload in background
    setTimeout(async () => {
      for (const table of commonTables) {
        try {
          await fetch(`/liblouis/tables/${table}`);
          console.log(`🔤 Preloaded braille table: ${table}`);
        } catch (error) {
          console.warn(`⚠️ Failed to preload table: ${table}`);
        }
      }
    }, 3000);
    
    // Monitor user patterns
    this.trackUserPatterns();
  }

  trackUserPatterns() {
    // Track frequently used settings
    document.addEventListener('stl-generation-start', (event) => {
      const settings = event.detail.settings;
      this.recordUsagePattern('shape_type', settings.shape_type);
      this.recordUsagePattern('card_size', `${settings.card_width}x${settings.card_height}`);
    });
  }

  async recordUsagePattern(pattern, value) {
    const key = `pattern_${pattern}`;
    const current = await this.getUserPreference(key, {});
    
    if (!current[value]) {
      current[value] = 0;
    }
    current[value]++;
    
    await this.saveUserPreference(key, current);
  }

  async getPopularPatterns(pattern) {
    const key = `pattern_${pattern}`;
    const patterns = await this.getUserPreference(key, {});
    
    // Sort by usage count
    return Object.entries(patterns)
      .sort((a, b) => b[1] - a[1])
      .map(([value, count]) => ({ value, count }));
  }

  // Smart cache eviction based on usage
  async smartCacheEviction() {
    const stats = await this.getCacheStats();
    
    if (stats && stats.stlFiles.totalSizeMB > 100) { // If cache > 100MB
      console.log('🧹 Starting smart cache eviction...');
      
      const db = await this.dbPromise;
      const tx = db.transaction('stl-files', 'readwrite');
      
      // Get all files sorted by timestamp
      const allFiles = await tx.store.getAll();
      allFiles.sort((a, b) => a.timestamp - b.timestamp);
      
      // Remove oldest 25% of files
      const filesToRemove = allFiles.slice(0, Math.floor(allFiles.length * 0.25));
      
      for (const file of filesToRemove) {
        await tx.store.delete(file.id);
        this.memoryCache.delete(file.hash);
      }
      
      await tx.done;
      
      console.log(`🧹 Smart eviction: removed ${filesToRemove.length} old STL files`);
    }
  }

  // Progressive asset loading
  async enableProgressiveLoading() {
    console.log('📈 Enabling progressive loading...');
    
    // Load critical assets first, then non-critical
    const criticalAssets = [
      '/main.js',
      '/liblouis/build-no-tables-utf16.js',
      '/liblouis/easy-api.js'
    ];
    
    const nonCriticalAssets = [
      '/geometry-worker.js',
      '/chunks/three-bvh-csg-*.js'
    ];
    
    // Load critical assets immediately
    for (const asset of criticalAssets) {
      this.preloadAsset(asset, 'high');
    }
    
    // Load non-critical assets with delay
    setTimeout(() => {
      for (const asset of nonCriticalAssets) {
        this.preloadAsset(asset, 'low');
      }
    }, 1000);
  }

  async preloadAsset(url, priority = 'low') {
    try {
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = url.endsWith('.js') ? 'script' : 'fetch';
      
      if (priority === 'high') {
        link.rel = 'preload';
      }
      
      document.head.appendChild(link);
      
      // Remove after loading to clean up DOM
      setTimeout(() => {
        if (link.parentNode) {
          link.parentNode.removeChild(link);
        }
      }, 5000);
      
    } catch (error) {
      console.warn(`⚠️ Failed to preload asset: ${url}`, error);
    }
  }

  // Adaptive quality based on device performance
  getAdaptiveSettings(baseSettings, devicePerformance) {
    const adaptedSettings = { ...baseSettings };
    
    // Reduce quality on low-end devices
    if ((devicePerformance.cores || 0) < 4 || devicePerformance.mobile) {
      adaptedSettings.geometry_resolution = 'medium';
      adaptedSettings.worker_batch_size = 25; // Smaller batches
      adaptedSettings.enable_progressive_generation = true;
    }
    
    // High-end device optimizations
    if ((devicePerformance.cores || 0) >= 8 && !devicePerformance.mobile) {
      adaptedSettings.geometry_resolution = 'high';
      adaptedSettings.worker_batch_size = 100; // Larger batches
      adaptedSettings.enable_parallel_workers = true;
    }
    
    return adaptedSettings;
  }

  async clearAllCaches() {
    try {
      // Clear IndexedDB
      const db = await this.dbPromise;
      const stores = ['stl-files', 'braille-translations', 'performance-metrics'];
      
      for (const storeName of stores) {
        const tx = db.transaction(storeName, 'readwrite');
        await tx.store.clear();
        await tx.done;
      }
      
      // Clear memory cache
      this.memoryCache.clear();
      
      // Clear service worker caches
      if (this.serviceWorker) {
        const messageChannel = new MessageChannel();
        
        messageChannel.port1.onmessage = (event) => {
          console.log('🗑️ All caches cleared successfully');
        };
        
        this.serviceWorker.active?.postMessage(
          { type: 'CLEAR_CACHE' },
          [messageChannel.port2]
        );
      }
      
    } catch (error) {
      console.error('❌ Failed to clear caches:', error);
    }
  }

  dispose() {
    if (this.serviceWorker) {
      // Cleanup if needed
    }
    
    this.memoryCache.clear();
    console.log('💾 Cache Manager disposed');
  }
}

/**
 * Liblouis Worker - Modernized Braille Translation Worker
 * Handles text to braille translation using liblouis library
 * Integrates with the new WorkerManager architecture
 */

let liblouisInstance = null;
let liblouisReady = false;

// Worker state
const workerState = {
  initialized: false,
  busy: false,
  lastJobId: null
};

console.log('🔤 Liblouis Worker loading...');

// Import liblouis scripts with error handling
async function loadLiblouisScripts() {
  try {
    console.log('Worker: Loading liblouis scripts...');
    
    // Try loading from public directory (Vite serves from public/)
    try {
      importScripts('/liblouis/build-no-tables-utf16.js');
      console.log('Worker: Loaded build-no-tables-utf16.js');
      importScripts('/liblouis/easy-api.js');
      console.log('Worker: Loaded easy-api.js');
      return true;
    } catch (error) {
      console.warn('Worker: Failed to load from /liblouis/, trying static paths:', error);
      
      // Fallback to static paths
      try {
        importScripts('/static/liblouis/build-no-tables-utf16.js');
        importScripts('/static/liblouis/easy-api.js');
        console.log('Worker: Loaded scripts from static directory');
        return true;
      } catch (altError) {
        console.error('Worker: All liblouis script paths failed:', altError);
        throw new Error(`Could not load liblouis scripts: ${error.message}`);
      }
    }
  } catch (error) {
    console.error('Worker: Critical error loading liblouis:', error);
    throw error;
  }
}

// Initialize liblouis in the worker
async function initializeLiblouis() {
  try {
    console.log('Worker: Initializing liblouis instance...');
    
    // Load the scripts first
    await loadLiblouisScripts();
    
    // Wait for scripts to be available
    await new Promise(resolve => setTimeout(resolve, 200));
    
    if (typeof liblouisBuild !== 'undefined' && typeof LiblouisEasyApi !== 'undefined') {
      console.log('Worker: Creating LiblouisEasyApi instance');
      liblouisInstance = new LiblouisEasyApi(liblouisBuild);
      
      // Enable on-demand table loading
      if (liblouisInstance.enableOnDemandTableLoading) {
        console.log('Worker: Enabling on-demand table loading...');
        try {
          // Try public directory first (Vite serves from public/)
          liblouisInstance.enableOnDemandTableLoading('/liblouis/tables/');
          console.log('Worker: Table loading enabled from public directory');
        } catch (e) {
          console.log('Worker: Public path failed, trying static path...');
          try {
            liblouisInstance.enableOnDemandTableLoading('/static/liblouis/tables/');
            console.log('Worker: Table loading enabled from static directory');
          } catch (altError) {
            console.warn('Worker: Could not enable on-demand table loading:', altError);
          }
        }
      }
      
      liblouisReady = true;
      workerState.initialized = true;
      console.log('✅ Liblouis worker initialized successfully');
      return true;
    } else {
      throw new Error('Liblouis libraries not available after loading');
    }
  } catch (error) {
    console.error('❌ Failed to initialize liblouis:', error);
    throw error;
  }
}

// Message handler
self.addEventListener('message', async (event) => {
  const { type, data, id, text, table } = event.data;
  
  console.log(`📨 Liblouis Worker received: ${type || 'legacy'} (${id || 'no-id'})`);

  try {
    switch (type) {
      case 'INIT':
        await handleInit(id);
        break;

      case 'TRANSLATE':
        await handleTranslate(data, id);
        break;

      case 'GET_STATUS':
        handleStatus(id);
        break;

      default:
        // Handle legacy format (direct text/table properties)
        if (text !== undefined) {
          await handleLegacyTranslate(text, table || 'en-us-g1.ctb', id);
        } else {
          throw new Error(`Unknown message type: ${type}`);
        }
    }
  } catch (error) {
    console.error('❌ Liblouis Worker error:', error);
    self.postMessage({
      type: 'ERROR',
      id,
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      }
    });
  }
});

/**
 * Handle worker initialization
 */
async function handleInit(id) {
  try {
    if (!workerState.initialized) {
      await initializeLiblouis();
    }
    
    self.postMessage({ 
      type: 'READY', 
      id,
      capabilities: {
        translation: true,
        tables: liblouisInstance ? ['en-us-g1.ctb', 'en-us-g2.ctb'] : [],
        onDemandLoading: liblouisInstance?.enableOnDemandTableLoading ? true : false
      }
    });
  } catch (error) {
    console.error('❌ Liblouis initialization failed:', error);
    throw new Error(`Liblouis initialization failed: ${error.message}`);
  }
}

/**
 * Handle text translation (modern format)
 */
async function handleTranslate(data, id) {
  if (!liblouisReady || !liblouisInstance) {
    throw new Error('Liblouis not ready. Call INIT first.');
  }

  const { text, table = 'en-us-g1.ctb', options = {} } = data;
  
  console.log(`🔄 Translating: "${text.substring(0, 50)}..." with table: ${table}`);
  
  workerState.busy = true;
  workerState.lastJobId = id;
  
  try {
    // Send progress update
    self.postMessage({
      type: 'PROGRESS',
      id,
      progress: 50,
      message: 'Translating text to braille...'
    });
    
    const result = liblouisInstance.translateString(table, text);
    
    self.postMessage({
      type: 'TRANSLATION_COMPLETE',
      id,
      result: {
        brailleText: result,
        originalText: text,
        table: table,
        stats: {
          originalLength: text.length,
          brailleLength: result.length,
          processingTime: Date.now() - Date.now() // Simple timing
        }
      }
    });
    
    console.log(`✅ Translation complete: ${result.length} braille characters`);
    
  } finally {
    workerState.busy = false;
    workerState.lastJobId = null;
  }
}

/**
 * Handle legacy translation format (backward compatibility)
 */
async function handleLegacyTranslate(text, table, id) {
  if (!liblouisReady || !liblouisInstance) {
    // Initialize if not ready (legacy behavior)
    await initializeLiblouis();
  }

  console.log(`🔄 Legacy translation: "${text.substring(0, 30)}..." with table: ${table}`);
  
  try {
    const result = liblouisInstance.translateString(table, text);
    
    // Send in legacy format
    self.postMessage({
      result: result,
      id: id
    });
    
    console.log(`✅ Legacy translation complete`);
    
  } catch (error) {
    console.error('❌ Legacy translation failed:', error);
    self.postMessage({
      error: error.message,
      id: id
    });
  }
}

/**
 * Handle status requests
 */
function handleStatus(id) {
  self.postMessage({
    type: 'STATUS',
    id,
    status: {
      ...workerState,
      liblouisReady,
      availableTables: liblouisInstance ? ['en-us-g1.ctb', 'en-us-g2.ctb'] : [],
      memoryUsage: performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null
    }
  });
}

// Error handlers
self.addEventListener('error', (event) => {
  console.error('🔥 Uncaught error in Liblouis Worker:', event);
  self.postMessage({
    type: 'ERROR',
    error: {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    }
  });
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('🔥 Unhandled promise rejection in Liblouis Worker:', event.reason);
  self.postMessage({
    type: 'ERROR',
    error: {
      message: event.reason.message || 'Unhandled promise rejection',
      stack: event.reason.stack
    }
  });
});

console.log('✅ Liblouis Worker loaded and ready for initialization');

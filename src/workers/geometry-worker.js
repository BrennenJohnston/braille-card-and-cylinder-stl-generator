/**
 * Geometry Worker - Main 3D Processing Worker
 * Handles BrailleGenerator and STLExporter operations in background thread
 */

// Import all required libraries for 3D processing
import { BrailleGenerator } from '../lib/braille-generator.js';
import { STLExporter } from '../lib/stl-exporter.js';
import { validateBrailleMatrix } from '../lib/braille-patterns.js';

let generator = null;
let exporter = null;
let currentJob = null;

// Worker state
const workerState = {
  initialized: false,
  busy: false,
  lastJobId: null
};

console.log('🔧 Geometry Worker loading...');

// Initialize worker on first message
self.addEventListener('message', async (event) => {
  const { type, data, id } = event.data;
  
  console.log(`📨 Geometry Worker received: ${type} (${id})`);

  try {
    switch (type) {
      case 'INIT':
        await initializeWorker(id);
        break;

      case 'GENERATE_CARD':
        await generateCard(data, id);
        break;

      case 'GENERATE_CYLINDER':
        await generateCylinder(data, id);
        break;

      case 'EXPORT_STL':
        await exportSTL(data, id);
        break;

      case 'CANCEL':
        await cancelJob(id);
        break;

      case 'GET_STATUS':
        sendStatus(id);
        break;

      default:
        throw new Error(`Unknown message type: ${type}`);
    }
  } catch (error) {
    console.error('❌ Geometry Worker error:', error);
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
 * Initialize worker with required libraries
 */
async function initializeWorker(id) {
  try {
    console.log('⚙️ Initializing Geometry Worker...');
    
    // Initialize the main libraries
    generator = new BrailleGenerator();
    exporter = new STLExporter();
    
    workerState.initialized = true;
    
    console.log('✅ Geometry Worker initialized successfully');
    
    self.postMessage({ 
      type: 'READY', 
      id,
      capabilities: {
        brailleGeneration: true,
        stlExport: true,
        cardGeneration: true,
        cylinderGeneration: true
      }
    });
    
  } catch (error) {
    console.error('❌ Worker initialization failed:', error);
    throw new Error(`Worker initialization failed: ${error.message}`);
  }
}

/**
 * Generate braille card geometry
 */
async function generateCard(data, id) {
  validateWorkerState();
  
  const { brailleLines, options = {} } = data;
  
  // Validate input data - expect braille Unicode text lines
  if (!brailleLines || !Array.isArray(brailleLines)) {
    throw new Error('Invalid brailleLines provided - expected array of braille Unicode strings');
  }
  
  console.log(`🏗️ Starting card generation for ${brailleLines.length} lines...`);
  
  workerState.busy = true;
  workerState.lastJobId = id;
  currentJob = { type: 'card', id, startTime: Date.now() };
  
  // Progress callback
  const updateProgress = (progress, message = null) => {
    if (workerState.lastJobId !== id) return; // Job was cancelled
    
    self.postMessage({
      type: 'PROGRESS',
      id,
      progress: Math.min(100, Math.max(0, progress)),
      message: message || `Processing braille dots: ${Math.round(progress)}%`,
      stage: 'generation'
    });
  };

  try {
    updateProgress(5, 'Initializing card generation...');
    
    // Generate geometry with progress updates
    const geometry = await generator.generateCard(brailleLines, {
      ...options,
      onProgress: (progress, message) => {
        // Map generator progress to our progress
        updateProgress(progress, message);
      }
    });
    
    if (workerState.lastJobId !== id) {
      console.log('🚫 Job was cancelled during generation');
      return;
    }
    
    // Calculate stats
    const stats = {
      vertices: geometry.attributes.position.count,
      faces: geometry.index ? geometry.index.count / 3 : geometry.attributes.position.count / 3,
      processingTime: Date.now() - currentJob.startTime
    };
    
    self.postMessage({
      type: 'GENERATION_COMPLETE',
      id,
      result: {
        geometry: {
          // Transfer geometry data safely
          positions: geometry.attributes.position.array,
          normals: geometry.attributes.normal?.array,
          indices: geometry.index?.array
        },
        stats
      }
    });
    
    console.log(`✅ Card generation complete: ${stats.faces} faces in ${stats.processingTime}ms`);
    
  } finally {
    workerState.busy = false;
    currentJob = null;
  }
}

/**
 * Generate braille cylinder geometry
 */
async function generateCylinder(data, id) {
  validateWorkerState();
  
  const { brailleLines, options = {} } = data;
  
  // Validate input data - expect braille Unicode text lines
  if (!brailleLines || !Array.isArray(brailleLines)) {
    throw new Error('Invalid brailleLines provided - expected array of braille Unicode strings');
  }
  
  console.log(`🥤 Starting cylinder generation for ${brailleLines.length} lines...`);
  
  workerState.busy = true;
  workerState.lastJobId = id;
  currentJob = { type: 'cylinder', id, startTime: Date.now() };
  
  const updateProgress = (progress, message = null) => {
    if (workerState.lastJobId !== id) return;
    
    self.postMessage({
      type: 'PROGRESS',
      id,
      progress: Math.min(100, Math.max(0, progress)),
      message: message || `Generating cylinder: ${Math.round(progress)}%`,
      stage: 'generation'
    });
  };

  try {
    updateProgress(10, 'Initializing cylinder generation...');
    
    // Generate cylinder geometry
    const geometry = await generator.generateCylinder(brailleLines, {
      ...options,
      onProgress: (progress, message) => {
        updateProgress(progress, message);
      }
    });
    
    if (workerState.lastJobId !== id) return;
    
    const stats = {
      vertices: geometry.attributes.position.count,
      faces: geometry.index ? geometry.index.count / 3 : geometry.attributes.position.count / 3,
      processingTime: Date.now() - currentJob.startTime
    };
    
    self.postMessage({
      type: 'GENERATION_COMPLETE',
      id,
      result: {
        geometry: {
          positions: geometry.attributes.position.array,
          normals: geometry.attributes.normal?.array,
          indices: geometry.index?.array
        },
        stats
      }
    });
    
    console.log(`✅ Cylinder generation complete: ${stats.faces} faces`);
    
  } finally {
    workerState.busy = false;
    currentJob = null;
  }
}

/**
 * Export geometry to STL format
 */
async function exportSTL(data, id) {
  validateWorkerState();
  
  const { geometry, format = 'binary' } = data;
  
  console.log(`📤 Exporting STL in ${format} format...`);
  
  workerState.busy = true;
  currentJob = { type: 'export', id, startTime: Date.now() };
  
  const updateProgress = (progress, message = null) => {
    if (workerState.lastJobId !== id) return;
    
    self.postMessage({
      type: 'PROGRESS',
      id,
      progress,
      message: message || `Exporting STL: ${Math.round(progress)}%`,
      stage: 'export'
    });
  };

  try {
    updateProgress(10, 'Preparing geometry for export...');
    
    // Reconstruct Three.js geometry from transferred data
    const reconstructedGeometry = await reconstructGeometry(geometry);
    
    updateProgress(30, 'Validating geometry...');
    
    // Validate geometry before export
    const isValid = exporter.validateGeometry(reconstructedGeometry);
    if (!isValid) {
      throw new Error('Geometry validation failed');
    }
    
    updateProgress(50, `Exporting to ${format} format...`);
    
    // Export based on format
    let result;
    if (format === 'binary') {
      result = exporter.exportBinary(reconstructedGeometry);
    } else if (format === 'ascii') {
      result = exporter.exportASCII(reconstructedGeometry);
    } else {
      throw new Error(`Unsupported export format: ${format}`);
    }
    
    updateProgress(90, 'Export complete, preparing download...');
    
    const stats = exporter.getStats(reconstructedGeometry);
    
    updateProgress(100, 'STL export ready!');
    
    // Transfer result with transferable objects for performance
    const transferList = format === 'binary' ? [result] : [];
    
    self.postMessage({
      type: 'EXPORT_COMPLETE',
      id,
      result: {
        data: result,
        format,
        stats: {
          ...stats,
          processingTime: Date.now() - currentJob.startTime
        }
      }
    }, transferList);
    
    console.log(`✅ STL export complete: ${stats.estimatedFileSize} bytes`);
    
  } finally {
    workerState.busy = false;
    currentJob = null;
  }
}

/**
 * Cancel current job
 */
async function cancelJob(id) {
  console.log(`🚫 Cancelling job: ${id}`);
  
  if (currentJob && currentJob.id === id) {
    workerState.lastJobId = null; // This stops progress updates
    currentJob = null;
    workerState.busy = false;
    
    self.postMessage({
      type: 'CANCELLED',
      id
    });
    
    console.log('✅ Job cancelled successfully');
  } else {
    console.log('⚠️ No matching job to cancel');
  }
}

/**
 * Send worker status
 */
function sendStatus(id) {
  self.postMessage({
    type: 'STATUS',
    id,
    status: {
      ...workerState,
      currentJob: currentJob ? {
        type: currentJob.type,
        id: currentJob.id,
        duration: Date.now() - currentJob.startTime
      } : null,
      memoryUsage: performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null
    }
  });
}

/**
 * Validate worker state before processing
 */
function validateWorkerState() {
  if (!workerState.initialized) {
    throw new Error('Worker not initialized. Call INIT first.');
  }
  
  if (!generator || !exporter) {
    throw new Error('Required libraries not loaded');
  }
}

/**
 * Reconstruct Three.js geometry from transferred data
 */
async function reconstructGeometry(geometryData) {
  // Import Three.js inside function to avoid issues
  const THREE = globalThis.THREE || (await import('three'));
  
  const geometry = new THREE.BufferGeometry();
  
  // Add position attribute
  if (geometryData.positions) {
    geometry.setAttribute('position', new THREE.BufferAttribute(geometryData.positions, 3));
  }
  
  // Add normal attribute if available
  if (geometryData.normals) {
    geometry.setAttribute('normal', new THREE.BufferAttribute(geometryData.normals, 3));
  }
  
  // Add index if available
  if (geometryData.indices) {
    geometry.setIndex(new THREE.BufferAttribute(geometryData.indices, 1));
  }
  
  return geometry;
}

// Error boundary for uncaught errors
self.addEventListener('error', (event) => {
  console.error('🔥 Uncaught error in Geometry Worker:', event);
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

// Handle promise rejections
self.addEventListener('unhandledrejection', (event) => {
  console.error('🔥 Unhandled promise rejection in Geometry Worker:', event.reason);
  self.postMessage({
    type: 'ERROR',
    error: {
      message: event.reason.message || 'Unhandled promise rejection',
      stack: event.reason.stack
    }
  });
});

console.log('✅ Geometry Worker loaded and ready for initialization');

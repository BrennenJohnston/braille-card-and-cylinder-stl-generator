/**
 * Braille STL Generator - Main Application Entry Point
 * Cloudflare Pages Client-Side Implementation
 */

import { BrailleGeneratorApp } from './App.js';
import './style.css';

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  console.log('🔧 Braille STL Generator v2.0 - Initializing...');
  
  // Feature detection
  try {
    const features = detectFeatures();
    console.log('✅ Feature detection passed:', features);
  } catch (error) {
    console.error('❌ Feature detection failed:', error.message);
    showError(error.message);
    return;
  }

  // Initialize the main application
  const appContainer = document.getElementById('app');
  if (!appContainer) {
    throw new Error('App container not found');
  }

  const app = new BrailleGeneratorApp(appContainer);
  
  // Handle page unload
  window.addEventListener('beforeunload', () => {
    app.destroy();
  });
  
  console.log('🚀 Application initialized successfully!');
});

/**
 * Detect required browser features
 */
function detectFeatures() {
  const features = {
    webgl: !!document.createElement('canvas').getContext('webgl2'),
    workers: typeof Worker !== 'undefined',
    wasm: typeof WebAssembly !== 'undefined',
    indexedDB: 'indexedDB' in window,
    serviceWorker: 'serviceWorker' in navigator,
    sharedArrayBuffer: typeof SharedArrayBuffer !== 'undefined',
    offscreenCanvas: typeof OffscreenCanvas !== 'undefined'
  };

  // Check for required features
  const required = ['webgl', 'workers', 'wasm'];
  const missing = required.filter(f => !features[f]);

  if (missing.length > 0) {
    throw new Error(
      `Your browser is missing required features: ${missing.join(', ')}. ` +
      `Please use a modern browser like Chrome, Firefox, or Edge.`
    );
  }

  return features;
}

/**
 * Show error message to user
 */
function showError(message) {
  document.body.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 2rem;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      text-align: center;
      background: #f5f5f5;
    ">
      <div style="
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        max-width: 600px;
      ">
        <h1 style="color: #e53e3e; margin-bottom: 1rem;">⚠️ Browser Compatibility Issue</h1>
        <p style="color: #4a5568; line-height: 1.6; margin-bottom: 1.5rem;">${message}</p>
        <p style="color: #718096; font-size: 0.9rem;">
          This application requires modern browser features for 3D processing and web workers.
        </p>
      </div>
    </div>
  `;
}

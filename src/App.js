/**
 * Main Application Component
 * Braille STL Generator - Complete UI Implementation
 */

import { WorkerManager } from './lib/worker-manager.js';
import { BrailleInput } from './components/BrailleInput.js';
import { ProgressBar } from './components/ProgressBar.js';
import { STLViewer } from './components/STLViewer.js';
import { downloadFile } from './utils/file-utils.js';

export class BrailleGeneratorApp {
  constructor(container) {
    this.container = container;
    this.workerManager = new WorkerManager();
    this.brailleInput = null;
    this.progressBar = null;
    this.stlViewer = null;
    this.currentJob = null;
    this.currentSTLData = null;
    
    console.log('📱 Initializing BrailleGeneratorApp with full UI...');
    this.init();
  }

  async init() {
    // Create complete UI structure
    this.container.innerHTML = `
      <div class="app-container">
        <header class="app-header">
          <h1>🔤 Braille Card & Cylinder STL Generator</h1>
          <p class="subtitle">Client-side processing powered by Cloudflare Pages</p>
          <div class="header-status">
            <span class="status-indicator">🌐</span>
            <span class="status-text">Phase 7: Cloudflare Pages Deployment Ready</span>
          </div>
        </header>
        
        <main class="app-main">
          <div class="main-grid">
            <!-- Input Section -->
            <section class="input-section">
              <div id="braille-input" class="component-container"></div>
            </section>
            
            <!-- Preview Section -->
            <section class="preview-section">
              <div id="stl-viewer" class="component-container"></div>
            </section>
          </div>
          
          <!-- Progress Section -->
          <section class="progress-section">
            <div id="progress-container" class="component-container"></div>
          </section>
        </main>
        
        <footer class="app-footer">
          <div class="footer-content">
            <div class="footer-info">
              <p>🌐 Processing happens entirely in your browser - no server required!</p>
              <p class="version">v2.0.0 - Cloudflare Pages Edition</p>
            </div>
            <div class="footer-actions">
              <button id="demo-btn" class="btn btn-outline">🎯 Load Demo</button>
              <button id="reset-btn" class="btn btn-outline">🔄 Reset</button>
            </div>
          </div>
        </footer>
      </div>
    `;

    console.log('🎨 UI structure created, initializing components...');
    await this.initializeComponents();
    this.setupEventHandlers();
    this.showWelcomeMessage();
    
    console.log('✨ Phase 5 complete - Full UI initialized!');
  }

  async initializeComponents() {
    try {
      // Initialize input component
      this.brailleInput = new BrailleInput(
        this.container.querySelector('#braille-input')
      );
      this.brailleInput.setWorkerManager(this.workerManager);
      
      // Initialize 3D viewer
      this.stlViewer = new STLViewer(
        this.container.querySelector('#stl-viewer')
      );
      
      // Initialize progress bar
      this.progressBar = new ProgressBar(
        this.container.querySelector('#progress-container')
      );
      
      console.log('✅ All UI components initialized');
      
    } catch (error) {
      console.error('❌ Component initialization failed:', error);
      this.showError('Failed to initialize components: ' + error.message);
    }
  }

  setupEventHandlers() {
    // Handle generate button click from input component
    this.brailleInput.addEventListener('generate', async (event) => {
      await this.generateSTL(event.detail);
    });
    
    // Handle download button click from viewer
    this.stlViewer.addEventListener('download', (event) => {
      this.handleDownload(event.detail);
    });
    
    // Handle new generation request
    this.stlViewer.addEventListener('new-generation', () => {
      this.startNewGeneration();
    });
    
    // Handle cancel button from progress bar
    this.progressBar.addEventListener('cancel', () => {
      this.cancelGeneration();
    });

    // Footer actions
    this.container.querySelector('#demo-btn').addEventListener('click', () => {
      this.loadDemo();
    });

    this.container.querySelector('#reset-btn').addEventListener('click', () => {
      this.resetApplication();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'Enter':
            e.preventDefault();
            if (this.brailleInput) {
              this.brailleInput.translateToBraille();
            }
            break;
          case 'g':
            e.preventDefault();
            if (!this.progressBar.isVisible) {
              const input = this.brailleInput.getCurrentInput();
              if (input.brailleLines.length > 0) {
                this.generateSTL(input);
              }
            }
            break;
        }
      }
    });
  }

  async generateSTL(data) {
    const { brailleLines, shapeType, settings, originalText } = data;
    
    try {
      console.log('🚀 Starting STL generation workflow...');
      console.log('Shape type:', shapeType);
      console.log('Lines:', brailleLines.length);
      
      // Disable UI during generation
      this.setUIEnabled(false);
      
      // Show progress
      this.progressBar.show('Starting generation...');
      this.stlViewer.clear();
      
      // Generate STL using worker
      const result = await this.workerManager.generateSTL(
        shapeType,
        brailleLines,
        settings,
        (progress, message) => {
          this.progressBar.setProgress(progress, message);
          console.log(`Progress: ${Math.round(progress)}% - ${message}`);
        }
      );
      
      // Show completion
      this.progressBar.setComplete(result.stats);
      
      // Load into viewer
      await this.stlViewer.loadSTL(result.stlBuffer, {
        ...result.stats,
        shapeType,
        originalText
      });
      
      this.currentSTLData = result.stlBuffer;
      
      // Show success
      this.showSuccessMessage(`STL generated successfully! ${this.formatFileSize(result.stats.fileSize)}`);
      
      // Hide progress after delay
      setTimeout(() => {
        this.progressBar.hide();
      }, 2000);
      
    } catch (error) {
      console.error('❌ STL generation failed:', error);
      this.progressBar.setError(error);
      this.showError('Generation failed: ' + error.message);
      
      setTimeout(() => {
        this.progressBar.hide();
      }, 3000);
    } finally {
      this.setUIEnabled(true);
    }
  }

  handleDownload(details) {
    console.log('💾 Download requested:', details);
    this.showSuccessMessage(`Download started: ${details.filename}`);
  }

  cancelGeneration() {
    if (this.currentJob) {
      console.log('🚫 Cancelling generation...');
      this.workerManager.cancelJob(this.currentJob);
      this.progressBar.setCancelled();
      
      setTimeout(() => {
        this.progressBar.hide();
        this.setUIEnabled(true);
      }, 1000);
    }
  }

  startNewGeneration() {
    console.log('🔄 Starting new generation');
    this.stlViewer.clear();
    this.progressBar.reset();
    this.currentSTLData = null;
  }

  loadDemo() {
    console.log('🎯 Loading demo content');
    this.brailleInput.loadExample('hello');
    this.showSuccessMessage('Demo text loaded! Click "Translate to Braille" then "Generate STL"');
  }

  resetApplication() {
    console.log('🔄 Resetting application');
    
    this.brailleInput.reset();
    this.stlViewer.clear();
    this.progressBar.reset();
    this.currentSTLData = null;
    this.currentJob = null;
    
    this.showSuccessMessage('Application reset successfully');
  }

  setUIEnabled(enabled) {
    this.brailleInput.setEnabled(enabled);
    
    const footerButtons = this.container.querySelectorAll('.footer-actions button');
    footerButtons.forEach(btn => {
      btn.disabled = !enabled;
    });
  }

  showWelcomeMessage() {
    setTimeout(() => {
      this.showSuccessMessage('🎉 Welcome! Enter text above and click "Load Demo" to get started.');
    }, 500);
  }

  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'app-notification error';
    errorDiv.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">⚠️</span>
        <span class="notification-text">${message}</span>
        <button class="notification-close">×</button>
      </div>
    `;
    
    this.container.appendChild(errorDiv);

    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.remove();
      }
    }, 5000);

    errorDiv.querySelector('.notification-close').addEventListener('click', () => {
      errorDiv.remove();
    });
  }

  showSuccessMessage(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'app-notification success';
    successDiv.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">✅</span>
        <span class="notification-text">${message}</span>
      </div>
    `;
    
    this.container.appendChild(successDiv);

    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.remove();
      }
    }, 3000);
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Get application state
  getState() {
    return {
      inputState: this.brailleInput?.getCurrentInput(),
      progressState: this.progressBar?.getState(),
      viewerState: this.stlViewer?.getState(),
      hasSTLData: !!this.currentSTLData,
      workersReady: this.workerManager?.areWorkersReady()
    };
  }

  destroy() {
    console.log('🧹 Destroying application...');
    
    if (this.workerManager) {
      this.workerManager.terminate();
    }
    if (this.stlViewer) {
      this.stlViewer.destroy();
    }
    
    console.log('✅ Application cleanup complete');
  }
}

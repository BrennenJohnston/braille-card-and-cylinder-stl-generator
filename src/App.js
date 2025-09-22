/**
 * Main Application Component
 * Braille STL Generator - Complete UI Implementation
 */

import { WorkerManager } from './lib/worker-manager.js';
import { BrailleInput } from './components/BrailleInput.js';
import { ProgressBar } from './components/ProgressBar.js';
import { STLViewer } from './components/STLViewer.js';
import { downloadFile } from './utils/file-utils.js';
import { PerformanceMonitor } from './lib/performance-monitor.js';
import { CacheManager } from './lib/cache-manager.js';

export class BrailleGeneratorApp {
  constructor(container) {
    this.container = container;
    this.workerManager = new WorkerManager();
    this.performanceMonitor = new PerformanceMonitor();
    this.cacheManager = new CacheManager();
    this.brailleInput = null;
    this.progressBar = null;
    this.stlViewer = null;
    this.currentJob = null;
    this.currentSTLData = null;
    
    console.log('📱 Initializing BrailleGeneratorApp with Phase 8 optimizations...');
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
            <span class="status-indicator">⚡</span>
            <span class="status-text">Phase 8: Performance Optimized - Live on Cloudflare Pages!</span>
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
    await this.initializePhase8Optimizations();
    this.showWelcomeMessage();
    
    console.log('✨ Phase 8 complete - Performance optimized application ready!');
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

  async initializePhase8Optimizations() {
    try {
      console.log('⚡ Initializing Phase 8 performance optimizations...');
      
      // Enable advanced caching
      await this.cacheManager.enablePredictiveCaching();
      
      // Enable performance monitoring  
      this.performanceMonitor.enableAutoOptimization();
      this.performanceMonitor.createPerformanceDashboard();
      
      // Enable progressive loading
      await this.cacheManager.enableProgressiveLoading();
      
      // Set up periodic cache maintenance
      setInterval(() => {
        this.cacheManager.smartCacheEviction();
      }, 5 * 60 * 1000); // Every 5 minutes
      
      console.log('✅ Phase 8 optimizations enabled');
      
    } catch (error) {
      console.error('❌ Phase 8 optimization setup failed:', error);
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
    
    // Check cache first (Phase 8 optimization)
    const cachedSTL = await this.cacheManager.getCachedSTL(originalText, brailleLines, settings);
    if (cachedSTL) {
      console.log('⚡ Loading STL from cache (instant!)');
      await this.stlViewer.loadSTL(cachedSTL.stlBuffer, {
        ...cachedSTL.stats,
        shapeType,
        originalText,
        fromCache: true
      });
      this.currentSTLData = cachedSTL.stlBuffer;
      this.showSuccessMessage(`STL loaded from cache! ${this.formatFileSize(cachedSTL.stats.fileSize)}`);
      return;
    }
    
    // Start performance monitoring
    const generationId = this.performanceMonitor.startSTLGeneration({
      shapeType,
      textLength: originalText.length,
      complexity: brailleLines.reduce((sum, line) => sum + line.length, 0)
    });
    
    try {
      console.log('🚀 Starting STL generation workflow...');
      console.log('Shape type:', shapeType);
      console.log('Lines:', brailleLines.length);
      
      // Disable UI during generation
      this.setUIEnabled(false);
      
      // Show progress
      this.progressBar.show('Starting generation...');
      this.stlViewer.clear();
      
      // Get adaptive settings based on device performance
      const devicePerformance = {
        cores: navigator.hardwareConcurrency || 4,
        mobile: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent),
        memory: performance.memory?.jsHeapSizeLimit || 0
      };
      
      const adaptedSettings = this.cacheManager.getAdaptiveSettings(settings, devicePerformance);
      console.log('🎯 Using adaptive settings for device performance');
      
      // Generate STL using worker
      const result = await this.workerManager.generateSTL(
        shapeType,
        brailleLines,
        adaptedSettings,
        (progress, message) => {
          this.progressBar.setProgress(progress, message);
          console.log(`Progress: ${Math.round(progress)}% - ${message}`);
        }
      );
      
      // End performance monitoring
      this.performanceMonitor.endSTLGeneration(generationId, {
        success: true,
        fileSize: result.stlBuffer.byteLength,
        triangles: result.stats.faces,
        duration: result.stats.totalTime
      });
      
      // Cache the result for future use (Phase 8 optimization)
      await this.cacheManager.cacheSTL(originalText, brailleLines, settings, result.stlBuffer, result.stats);
      
      // Show completion
      this.progressBar.setComplete(result.stats);
      
      // Load into viewer
      await this.stlViewer.loadSTL(result.stlBuffer, {
        ...result.stats,
        shapeType,
        originalText
      });
      
      this.currentSTLData = result.stlBuffer;
      
      // Show success with performance info
      const perfInfo = result.stats.totalTime < 5000 ? 
        ` (⚡ ${(result.stats.totalTime / 1000).toFixed(1)}s)` : 
        ` (${(result.stats.totalTime / 1000).toFixed(1)}s)`;
      
      this.showSuccessMessage(`STL generated successfully! ${this.formatFileSize(result.stats.fileSize)}${perfInfo}`);
      
      // Dispatch custom event for analytics
      document.dispatchEvent(new CustomEvent('stl-generation-complete', {
        detail: {
          duration: result.stats.totalTime,
          shapeType,
          fileSize: result.stlBuffer.byteLength,
          success: true
        }
      }));
      
      // Hide progress after delay
      setTimeout(() => {
        this.progressBar.hide();
      }, 2000);
      
    } catch (error) {
      console.error('❌ STL generation failed:', error);
      
      // End performance monitoring with error
      this.performanceMonitor.endSTLGeneration(generationId, {
        success: false,
        error: error.message
      });
      
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

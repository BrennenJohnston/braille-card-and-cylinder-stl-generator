/**
 * STLViewer Component - 3D preview and download interface
 * Displays generated STL models with interactive controls
 */

export class STLViewer extends EventTarget {
  constructor(container) {
    super();
    this.container = container;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.currentMesh = null;
    this.currentSTLData = null;
    this.animationId = null;
    
    console.log('👁️ STLViewer component initializing...');
    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="stl-viewer-container">
        <div class="viewer-header">
          <h2>👁️ 3D Preview</h2>
          <div class="viewer-controls">
            <button id="reset-view" class="btn btn-icon" title="Reset View">
              🔄
            </button>
            <button id="wireframe-toggle" class="btn btn-icon" title="Toggle Wireframe">
              📐
            </button>
            <button id="fullscreen-btn" class="btn btn-icon" title="Fullscreen">
              ⛶
            </button>
          </div>
        </div>

        <div class="viewer-canvas-container">
          <canvas id="stl-canvas"></canvas>
          <div class="viewer-overlay" id="viewer-overlay">
            <div class="overlay-content">
              <div class="overlay-icon">🎯</div>
              <h3>Ready for STL Generation</h3>
              <p>Your 3D model will appear here after generation</p>
            </div>
          </div>
          
          <div class="viewer-loading" id="viewer-loading" style="display: none;">
            <div class="loading-spinner"></div>
            <p>Loading 3D model...</p>
          </div>
        </div>

        <div class="viewer-info">
          <div class="model-stats" id="model-stats" style="display: none;">
            <div class="stat-item">
              <span class="stat-label">Vertices:</span>
              <span class="stat-value" id="vertices-count">--</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Faces:</span>
              <span class="stat-value" id="faces-count">--</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">File Size:</span>
              <span class="stat-value" id="file-size">--</span>
            </div>
          </div>
          
          <div class="viewer-actions" id="viewer-actions" style="display: none;">
            <button id="download-btn" class="btn btn-success">
              💾 Download STL
            </button>
            <button id="download-ascii-btn" class="btn btn-secondary">
              📄 Download ASCII
            </button>
            <button id="new-generation-btn" class="btn btn-primary">
              🔄 Generate New
            </button>
          </div>
        </div>

        <div class="viewer-help">
          <div class="help-item">
            <span class="help-icon">🖱️</span>
            <span class="help-text">Left click + drag to rotate</span>
          </div>
          <div class="help-item">
            <span class="help-icon">🔍</span>
            <span class="help-text">Scroll to zoom in/out</span>
          </div>
          <div class="help-item">
            <span class="help-icon">✋</span>
            <span class="help-text">Right click + drag to pan</span>
          </div>
        </div>
      </div>
    `;

    this.canvas = this.container.querySelector('#stl-canvas');
    this.overlay = this.container.querySelector('#viewer-overlay');
    this.loading = this.container.querySelector('#viewer-loading');
    this.modelStats = this.container.querySelector('#model-stats');
    this.viewerActions = this.container.querySelector('#viewer-actions');

    this.setupEventListeners();
    this.setupThreeJS();
  }

  setupEventListeners() {
    // Control buttons
    const resetView = this.container.querySelector('#reset-view');
    const wireframeToggle = this.container.querySelector('#wireframe-toggle');
    const fullscreenBtn = this.container.querySelector('#fullscreen-btn');
    const downloadBtn = this.container.querySelector('#download-btn');
    const downloadAsciiBtn = this.container.querySelector('#download-ascii-btn');
    const newGenerationBtn = this.container.querySelector('#new-generation-btn');

    if (resetView) {
      resetView.addEventListener('click', () => {
        this.resetView();
      });
    }

    if (wireframeToggle) {
      wireframeToggle.addEventListener('click', () => {
        this.toggleWireframe();
      });
    }

    if (fullscreenBtn) {
      fullscreenBtn.addEventListener('click', () => {
        this.toggleFullscreen();
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => {
        this.downloadSTL('binary');
      });
    }

    if (downloadAsciiBtn) {
      downloadAsciiBtn.addEventListener('click', () => {
        this.downloadSTL('ascii');
      });
    }

    if (newGenerationBtn) {
      newGenerationBtn.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('new-generation'));
      });
    }

    // Handle window resize
    window.addEventListener('resize', () => {
      this.handleResize();
    });
  }

  async setupThreeJS() {
    try {
      console.log('🎬 Setting up Three.js scene...');
      
      // For Phase 5, create a simple preview setup
      // In production, this would use full Three.js with STLLoader
      this.mockThreeJSSetup();
      
      console.log('✅ Three.js scene setup complete');
      
    } catch (error) {
      console.error('❌ Three.js setup failed:', error);
      this.showError('Failed to initialize 3D viewer');
    }
  }

  mockThreeJSSetup() {
    // Mock Three.js setup for Phase 5
    console.log('🎭 Mock Three.js setup for Phase 5');
    
    // Simulate canvas setup
    this.canvas.width = this.canvas.offsetWidth || 400;
    this.canvas.height = this.canvas.offsetHeight || 300;
    
    const ctx = this.canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#f7fafc';
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      
      // Draw placeholder content
      ctx.fillStyle = '#4a5568';
      ctx.font = '16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('3D Preview Ready', this.canvas.width / 2, this.canvas.height / 2);
    }
  }

  async loadSTL(stlBuffer, stats = {}) {
    console.log('📤 Loading STL into viewer...', { 
      size: stlBuffer.byteLength, 
      stats 
    });

    this.currentSTLData = stlBuffer;
    
    try {
      this.showLoading(true);
      this.hideOverlay();
      
      // Simulate loading delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock STL loading for Phase 5
      await this.mockLoadSTL(stlBuffer, stats);
      
      this.updateModelStats(stats);
      this.showViewerActions(true);
      this.showLoading(false);
      
      console.log('✅ STL loaded successfully');
      
    } catch (error) {
      console.error('❌ Failed to load STL:', error);
      this.showError('Failed to load STL model');
      this.showLoading(false);
    }
  }

  async mockLoadSTL(stlBuffer, stats) {
    console.log('🎭 Mock STL loading for Phase 5');
    
    // Simulate STL parsing and display
    const ctx = this.canvas.getContext('2d');
    if (ctx) {
      // Clear canvas
      ctx.fillStyle = '#1a202c';
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      
      // Draw mock 3D model representation
      const centerX = this.canvas.width / 2;
      const centerY = this.canvas.height / 2;
      
      // Draw card or cylinder based on type
      ctx.strokeStyle = '#4299e1';
      ctx.lineWidth = 2;
      
      if (stats.shapeType === 'cylinder') {
        // Draw cylinder representation
        ctx.beginPath();
        ctx.ellipse(centerX, centerY - 20, 40, 15, 0, 0, 2 * Math.PI);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.ellipse(centerX, centerY + 20, 40, 15, 0, 0, 2 * Math.PI);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(centerX - 40, centerY - 20);
        ctx.lineTo(centerX - 40, centerY + 20);
        ctx.moveTo(centerX + 40, centerY - 20);
        ctx.lineTo(centerX + 40, centerY + 20);
        ctx.stroke();
      } else {
        // Draw card representation
        ctx.strokeRect(centerX - 60, centerY - 30, 120, 60);
        
        // Draw some dots
        ctx.fillStyle = '#4299e1';
        for (let i = 0; i < 6; i++) {
          for (let j = 0; j < 3; j++) {
            const x = centerX - 40 + (i * 15);
            const y = centerY - 15 + (j * 15);
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, 2 * Math.PI);
            ctx.fill();
          }
        }
      }
      
      // Add title
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '14px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('Braille Model Preview', centerX, 30);
      ctx.fillText(`${stats.vertices || 0} vertices, ${stats.faces || 0} faces`, centerX, this.canvas.height - 20);
    }
  }

  updateModelStats(stats) {
    this.container.querySelector('#vertices-count').textContent = 
      stats.vertices ? stats.vertices.toLocaleString() : '--';
    
    this.container.querySelector('#faces-count').textContent = 
      stats.faces ? stats.faces.toLocaleString() : '--';
    
    this.container.querySelector('#file-size').textContent = 
      stats.fileSize ? this.formatFileSize(stats.fileSize) : '--';
    
    this.modelStats.style.display = 'flex';
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  showLoading(show) {
    this.loading.style.display = show ? 'flex' : 'none';
  }

  hideOverlay() {
    this.overlay.style.display = 'none';
  }

  showViewerActions(show) {
    this.viewerActions.style.display = show ? 'flex' : 'none';
  }

  resetView() {
    console.log('🔄 Resetting view');
    // In production, this would reset Three.js camera position
    if (this.currentSTLData) {
      this.mockLoadSTL(this.currentSTLData, {});
    }
  }

  toggleWireframe() {
    console.log('📐 Toggling wireframe');
    // In production, this would toggle Three.js material wireframe
    const btn = this.container.querySelector('#wireframe-toggle');
    btn.classList.toggle('active');
  }

  toggleFullscreen() {
    console.log('⛶ Toggling fullscreen');
    
    if (!document.fullscreenElement) {
      this.container.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }

  downloadSTL(format = 'binary') {
    if (!this.currentSTLData) {
      this.showError('No STL data available for download');
      return;
    }

    console.log(`💾 Downloading STL in ${format} format...`);
    
    try {
      let blob, filename;
      
      if (format === 'binary') {
        blob = new Blob([this.currentSTLData], { 
          type: 'application/octet-stream' 
        });
        filename = `braille_model_${Date.now()}.stl`;
      } else {
        // For ASCII format, we'd need to convert the binary data
        // For Phase 5, just download the binary as ASCII extension
        blob = new Blob([this.currentSTLData], { 
          type: 'text/plain' 
        });
        filename = `braille_model_${Date.now()}_ascii.stl`;
      }
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      URL.revokeObjectURL(url);
      
      this.dispatchEvent(new CustomEvent('download', {
        detail: { format, filename, size: blob.size }
      }));
      
      console.log(`✅ STL download initiated: ${filename} (${this.formatFileSize(blob.size)})`);
      
    } catch (error) {
      console.error('❌ Download failed:', error);
      this.showError('Download failed: ' + error.message);
    }
  }

  showError(message) {
    // Remove existing error
    const existingError = this.container.querySelector('.viewer-error');
    if (existingError) {
      existingError.remove();
    }

    // Create error overlay
    const errorDiv = document.createElement('div');
    errorDiv.className = 'viewer-error';
    errorDiv.innerHTML = `
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span class="error-text">${message}</span>
        <button class="error-close">×</button>
      </div>
    `;
    
    this.container.appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.remove();
      }
    }, 5000);

    // Manual close
    errorDiv.querySelector('.error-close').addEventListener('click', () => {
      errorDiv.remove();
    });
  }

  clear() {
    console.log('🧹 Clearing STL viewer');
    
    this.currentMesh = null;
    this.currentSTLData = null;
    
    // Show overlay again
    this.overlay.style.display = 'flex';
    this.modelStats.style.display = 'none';
    this.viewerActions.style.display = 'none';
    
    // Clear canvas
    const ctx = this.canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#f7fafc';
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }

  handleResize() {
    if (!this.canvas) return;
    
    const rect = this.container.getBoundingClientRect();
    this.canvas.width = rect.width - 40; // Account for padding
    this.canvas.height = Math.max(300, rect.height - 100);
    
    // Redraw current content
    if (this.currentSTLData) {
      this.mockLoadSTL(this.currentSTLData, {});
    } else {
      this.mockThreeJSSetup();
    }
  }

  mockThreeJSSetup() {
    // Mock setup for Phase 5
    const ctx = this.canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#f7fafc';
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }

  // Get viewer state
  getState() {
    return {
      hasModel: !!this.currentSTLData,
      modelLoaded: !!this.currentMesh,
      canvasSize: {
        width: this.canvas.width,
        height: this.canvas.height
      },
      currentSTLSize: this.currentSTLData ? this.currentSTLData.byteLength : 0
    };
  }

  // Set loading state
  setLoading(loading, message = 'Loading...') {
    this.showLoading(loading);
    if (loading) {
      const loadingText = this.loading.querySelector('p');
      if (loadingText) {
        loadingText.textContent = message;
      }
    }
  }

  // Show success message
  showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'viewer-success';
    successDiv.innerHTML = `
      <div class="success-content">
        <span class="success-icon">✅</span>
        <span class="success-text">${message}</span>
      </div>
    `;
    
    this.container.appendChild(successDiv);

    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.remove();
      }
    }, 3000);
  }

  // Cleanup resources
  destroy() {
    console.log('🧹 Destroying STL viewer');
    
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    
    // In production, would dispose Three.js resources
    this.currentMesh = null;
    this.currentSTLData = null;
    
    console.log('✅ STL viewer cleanup complete');
  }
}

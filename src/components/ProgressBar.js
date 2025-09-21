/**
 * ProgressBar Component - Real-time progress tracking
 * Shows generation progress with cancellation support
 */

export class ProgressBar extends EventTarget {
  constructor(container) {
    super();
    this.container = container;
    this.currentProgress = 0;
    this.currentMessage = '';
    this.startTime = null;
    this.isVisible = false;
    
    console.log('📊 ProgressBar component initializing...');
    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="progress-bar-wrapper" style="display: none;">
        <div class="progress-header">
          <h3>🔄 Processing Braille STL</h3>
          <button class="cancel-button" title="Cancel generation">
            <span class="cancel-icon">×</span>
          </button>
        </div>
        
        <div class="progress-info">
          <div class="progress-message">Initializing...</div>
          <div class="progress-details">
            <span class="progress-percentage">0%</span>
            <span class="progress-time">--:--</span>
          </div>
        </div>
        
        <div class="progress-bar">
          <div class="progress-fill" style="width: 0%;"></div>
          <div class="progress-stages">
            <div class="stage" data-stage="translate">🔤</div>
            <div class="stage" data-stage="generate">🏗️</div>
            <div class="stage" data-stage="export">📤</div>
            <div class="stage" data-stage="complete">✅</div>
          </div>
        </div>
        
        <div class="progress-stats">
          <div class="stat">
            <span class="stat-label">Status:</span>
            <span class="stat-value" id="status-value">Ready</span>
          </div>
          <div class="stat">
            <span class="stat-label">Stage:</span>
            <span class="stat-value" id="stage-value">Waiting</span>
          </div>
          <div class="stat">
            <span class="stat-label">Estimated:</span>
            <span class="stat-value" id="estimate-value">--</span>
          </div>
        </div>
      </div>
    `;

    this.wrapper = this.container.querySelector('.progress-bar-wrapper');
    this.messageElement = this.container.querySelector('.progress-message');
    this.percentageElement = this.container.querySelector('.progress-percentage');
    this.timeElement = this.container.querySelector('.progress-time');
    this.fillElement = this.container.querySelector('.progress-fill');
    this.cancelButton = this.container.querySelector('.cancel-button');
    this.stagesElement = this.container.querySelector('.progress-stages');
    
    this.statusValue = this.container.querySelector('#status-value');
    this.stageValue = this.container.querySelector('#stage-value');
    this.estimateValue = this.container.querySelector('#estimate-value');

    this.setupEventListeners();
  }

  setupEventListeners() {
    this.cancelButton.addEventListener('click', () => {
      console.log('🚫 User requested cancellation');
      this.dispatchEvent(new CustomEvent('cancel'));
    });

    // Keyboard shortcut for cancel (Escape key)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isVisible) {
        this.dispatchEvent(new CustomEvent('cancel'));
      }
    });
  }

  show(initialMessage = 'Starting generation...') {
    this.isVisible = true;
    this.startTime = Date.now();
    
    if (this.wrapper) {
      this.wrapper.style.display = 'block';
      
      // Smooth fade in
      this.wrapper.style.opacity = '0';
      setTimeout(() => {
        if (this.wrapper) {
          this.wrapper.style.opacity = '1';
        }
      }, 10);
    }
    
    this.setProgress(0, initialMessage);
    this.updateStage('translate');
    
    if (this.statusValue) {
      this.statusValue.textContent = 'Running';
    }
    
    console.log('📊 Progress bar shown');
  }

  hide() {
    this.isVisible = false;
    
    // Smooth fade out
    this.wrapper.style.opacity = '0';
    setTimeout(() => {
      this.wrapper.style.display = 'none';
    }, 300);
    
    console.log('📊 Progress bar hidden');
  }

  setProgress(value, message = null) {
    this.currentProgress = Math.min(100, Math.max(0, value));
    this.currentMessage = message || this.currentMessage;
    
    // Update percentage
    if (this.percentageElement) {
      this.percentageElement.textContent = `${Math.round(this.currentProgress)}%`;
    }
    
    // Update progress bar
    if (this.fillElement) {
      this.fillElement.style.width = `${this.currentProgress}%`;
      
      // Update color based on progress
      if (this.currentProgress < 30) {
        this.fillElement.style.background = 'linear-gradient(90deg, #4299e1, #3182ce)';
      } else if (this.currentProgress < 70) {
        this.fillElement.style.background = 'linear-gradient(90deg, #ed8936, #dd6b20)';
      } else {
        this.fillElement.style.background = 'linear-gradient(90deg, #48bb78, #38a169)';
      }
    }
    
    // Update message
    if (message && this.messageElement) {
      this.messageElement.textContent = message;
    }
    
    // Update elapsed time
    if (this.startTime && this.timeElement) {
      const elapsed = Date.now() - this.startTime;
      const minutes = Math.floor(elapsed / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);
      this.timeElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Update estimated completion
    if (this.currentProgress > 5 && this.startTime && this.estimateValue) {
      const elapsed = Date.now() - this.startTime;
      const estimated = (elapsed / this.currentProgress) * (100 - this.currentProgress);
      const estMinutes = Math.floor(estimated / 60000);
      const estSeconds = Math.floor((estimated % 60000) / 1000);
      
      if (estimated > 2000) { // Only show if more than 2 seconds left
        this.estimateValue.textContent = `${estMinutes}:${estSeconds.toString().padStart(2, '0')} remaining`;
      } else {
        this.estimateValue.textContent = 'Almost done!';
      }
    }
    
    // Update stage indicators
    this.updateStageProgress(this.currentProgress);
  }

  setMessage(message) {
    this.currentMessage = message;
    if (this.messageElement) {
      this.messageElement.textContent = message;
    }
    if (this.stageValue) {
      this.stageValue.textContent = message;
    }
  }

  updateStage(stage) {
    if (!this.stagesElement) return;
    
    // Remove active class from all stages
    const stages = this.stagesElement.querySelectorAll('.stage');
    stages.forEach(s => s.classList.remove('active', 'complete'));
    
    // Activate current stage
    const currentStage = this.stagesElement.querySelector(`[data-stage="${stage}"]`);
    if (currentStage) {
      currentStage.classList.add('active');
    }
    
    // Mark previous stages as complete
    const stageOrder = ['translate', 'generate', 'export', 'complete'];
    const currentIndex = stageOrder.indexOf(stage);
    
    for (let i = 0; i < currentIndex; i++) {
      const prevStage = this.stagesElement.querySelector(`[data-stage="${stageOrder[i]}"]`);
      if (prevStage) {
        prevStage.classList.remove('active');
        prevStage.classList.add('complete');
      }
    }
  }

  updateStageProgress(progress) {
    // Map progress to stages
    if (progress < 10) {
      this.updateStage('translate');
    } else if (progress < 90) {
      this.updateStage('generate');
    } else if (progress < 100) {
      this.updateStage('export');
    } else {
      this.updateStage('complete');
    }
  }

  setError(error) {
    if (this.fillElement) {
      this.fillElement.style.background = 'linear-gradient(90deg, #e53e3e, #c53030)';
    }
    
    if (this.messageElement) {
      this.messageElement.textContent = `Error: ${error.message || error}`;
    }
    
    if (this.statusValue) {
      this.statusValue.textContent = 'Error';
    }
    
    if (this.estimateValue) {
      this.estimateValue.textContent = 'Failed';
    }
    
    // Show error state
    if (this.wrapper) {
      this.wrapper.classList.add('error-state');
    }
    
    console.error('❌ Progress bar error:', error);
  }

  setComplete(stats = {}) {
    this.setProgress(100, 'Generation complete!');
    this.updateStage('complete');
    
    if (this.statusValue) {
      this.statusValue.textContent = 'Complete';
    }
    
    if (this.estimateValue) {
      this.estimateValue.textContent = 'Done!';
    }
    
    // Show completion stats if available
    if (stats.fileSize && this.stageValue) {
      const sizeKB = (stats.fileSize / 1024).toFixed(1);
      this.stageValue.textContent = `STL ready (${sizeKB} KB)`;
    }
    
    if (stats.processingTime && this.messageElement) {
      const timeMs = stats.processingTime;
      const timeSec = (timeMs / 1000).toFixed(1);
      this.messageElement.textContent = `Complete in ${timeSec}s!`;
    }
    
    // Flash success
    if (this.wrapper) {
      this.wrapper.classList.add('success-flash');
      setTimeout(() => {
        if (this.wrapper) {
          this.wrapper.classList.remove('success-flash');
        }
      }, 1000);
    }
    
    console.log('✅ Progress bar complete:', stats);
  }

  setCancelled() {
    if (this.fillElement) {
      this.fillElement.style.background = 'linear-gradient(90deg, #a0aec0, #718096)';
    }
    
    if (this.messageElement) {
      this.messageElement.textContent = 'Generation cancelled';
    }
    
    if (this.statusValue) {
      this.statusValue.textContent = 'Cancelled';
    }
    
    if (this.estimateValue) {
      this.estimateValue.textContent = 'Stopped';
    }
    
    console.log('🚫 Progress bar cancelled');
  }

  reset() {
    this.currentProgress = 0;
    this.currentMessage = '';
    this.startTime = null;
    
    this.wrapper.classList.remove('error-state', 'success-flash');
    this.setProgress(0, 'Ready');
    this.statusValue.textContent = 'Ready';
    this.stageValue.textContent = 'Waiting';
    this.estimateValue.textContent = '--';
    
    // Reset all stages
    const stages = this.stagesElement.querySelectorAll('.stage');
    stages.forEach(s => s.classList.remove('active', 'complete'));
    
    console.log('🔄 Progress bar reset');
  }

  // Get current progress state
  getState() {
    return {
      progress: this.currentProgress,
      message: this.currentMessage,
      visible: this.isVisible,
      startTime: this.startTime,
      elapsedTime: this.startTime ? Date.now() - this.startTime : 0
    };
  }
}

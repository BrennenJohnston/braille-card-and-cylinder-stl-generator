/**
 * BrailleInput Component - Text input and configuration interface
 * Handles text entry, braille translation, and generation settings
 */

export class BrailleInput extends EventTarget {
  constructor(container) {
    super();
    this.container = container;
    this.workerManager = null;
    this.currentText = '';
    this.currentBraille = '';
    this.settings = {
      shape_type: 'card',
      card_width: 85.60,
      card_height: 53.98,
      card_thickness: 0.76,
      grid_columns: 32,
      grid_rows: 4,
      use_rounded_dots: false,
      cylinder_params: {
        diameter_mm: 31.35,
        height_mm: 53.98
      }
    };
    
    console.log('📝 BrailleInput component initializing...');
    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="braille-input-container">
        <div class="input-header">
          <h2>📝 Braille Text Input</h2>
          <p>Enter text to convert to braille and generate 3D models</p>
        </div>

        <div class="input-section">
          <div class="text-input-area">
            <label for="text-input">Text to Convert:</label>
            <textarea 
              id="text-input" 
              placeholder="Enter your text here (up to 4 lines, ~30 characters per line)&#10;Example: HELLO WORLD"
              maxlength="500"
              rows="4"
            ></textarea>
            <div class="input-info">
              <span class="char-count">0/500 characters</span>
              <button id="translate-btn" class="btn btn-secondary">🔤 Translate to Braille</button>
            </div>
          </div>

          <div class="braille-preview-area">
            <label>Braille Preview:</label>
            <div id="braille-preview" class="braille-display">
              <span class="placeholder">Braille characters will appear here...</span>
            </div>
            <div class="braille-info">
              <span id="braille-stats">0 characters, 0 dots</span>
            </div>
          </div>
        </div>

        <div class="settings-section">
          <h3>⚙️ Generation Settings</h3>
          
          <div class="settings-grid">
            <div class="setting-group">
              <label>Shape Type:</label>
              <select id="shape-type">
                <option value="card">📇 Braille Card</option>
                <option value="cylinder">🥤 Braille Cylinder</option>
              </select>
            </div>

            <div class="setting-group">
              <label>Card Width (mm):</label>
              <input type="number" id="card-width" value="85.60" min="10" max="200" step="0.1">
            </div>

            <div class="setting-group">
              <label>Card Height (mm):</label>
              <input type="number" id="card-height" value="53.98" min="10" max="200" step="0.1">
            </div>

            <div class="setting-group">
              <label>Thickness (mm):</label>
              <input type="number" id="card-thickness" value="0.76" min="0.1" max="10" step="0.01">
            </div>

            <div class="setting-group">
              <label>Grid Columns:</label>
              <input type="number" id="grid-columns" value="32" min="5" max="50" step="1">
            </div>

            <div class="setting-group">
              <label>Grid Rows:</label>
              <input type="number" id="grid-rows" value="4" min="1" max="10" step="1">
            </div>

            <div class="setting-group setting-checkbox">
              <label>
                <input type="checkbox" id="use-rounded-dots">
                <span class="checkmark"></span>
                Use Rounded Dots
              </label>
            </div>
          </div>

          <div id="cylinder-settings" class="cylinder-settings" style="display: none;">
            <h4>🥤 Cylinder Settings</h4>
            <div class="settings-grid">
              <div class="setting-group">
                <label>Diameter (mm):</label>
                <input type="number" id="cylinder-diameter" value="31.35" min="10" max="100" step="0.1">
              </div>
              <div class="setting-group">
                <label>Height (mm):</label>
                <input type="number" id="cylinder-height" value="53.98" min="10" max="200" step="0.1">
              </div>
            </div>
          </div>
        </div>

        <div class="action-section">
          <button id="generate-btn" class="btn btn-primary" disabled>
            🚀 Generate STL File
          </button>
          <div class="action-info">
            <p>💡 Processing happens entirely in your browser - no server required!</p>
          </div>
        </div>
      </div>
    `;

    this.setupEventListeners();
    this.updateCharCount();
    this.updateGenerateButton();
  }

  setupEventListeners() {
    // Text input handling
    const textInput = this.container.querySelector('#text-input');
    const translateBtn = this.container.querySelector('#translate-btn');
    const generateBtn = this.container.querySelector('#generate-btn');
    const shapeType = this.container.querySelector('#shape-type');
    
    // Settings inputs
    const settingsInputs = this.container.querySelectorAll('input, select');

    if (textInput) {
      textInput.addEventListener('input', (e) => {
        this.currentText = e.target.value;
        this.updateCharCount();
        this.updateGenerateButton();
      });

      // Enter key in text area triggers translation
      textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
          e.preventDefault();
          this.translateToBraille();
        }
      });
    }

    if (translateBtn) {
      translateBtn.addEventListener('click', () => {
        this.translateToBraille();
      });
    }

    if (generateBtn) {
      generateBtn.addEventListener('click', () => {
        this.startGeneration();
      });
    }

    if (shapeType) {
      shapeType.addEventListener('change', (e) => {
        this.settings.shape_type = e.target.value;
        this.updateCylinderSettings();
      });
    }

    // Settings change handlers
    settingsInputs.forEach(input => {
      input.addEventListener('change', () => {
        this.updateSettings();
      });
    });
  }

  updateCharCount() {
    const charCount = this.container.querySelector('.char-count');
    if (!charCount) return;
    
    charCount.textContent = `${this.currentText.length}/500 characters`;
    
    if (this.currentText.length > 400) {
      charCount.style.color = '#e53e3e';
    } else if (this.currentText.length > 300) {
      charCount.style.color = '#dd6b20';
    } else {
      charCount.style.color = '#4a5568';
    }
  }

  updateCylinderSettings() {
    const cylinderSettings = this.container.querySelector('#cylinder-settings');
    if (!cylinderSettings) return;
    
    const isCard = this.settings.shape_type === 'card';
    cylinderSettings.style.display = isCard ? 'none' : 'block';
  }

  updateSettings() {
    const inputs = {
      card_width: '#card-width',
      card_height: '#card-height', 
      card_thickness: '#card-thickness',
      grid_columns: '#grid-columns',
      grid_rows: '#grid-rows',
      use_rounded_dots: '#use-rounded-dots'
    };

    for (const [key, selector] of Object.entries(inputs)) {
      const element = this.container.querySelector(selector);
      if (element) {
        if (element.type === 'checkbox') {
          this.settings[key] = element.checked;
        } else {
          this.settings[key] = parseFloat(element.value) || 0;
        }
      }
    }

    // Cylinder settings
    this.settings.cylinder_params = {
      diameter_mm: parseFloat(this.container.querySelector('#cylinder-diameter')?.value) || 31.35,
      height_mm: parseFloat(this.container.querySelector('#cylinder-height')?.value) || 53.98
    };

    console.log('⚙️ Settings updated:', this.settings);
  }

  updateGenerateButton() {
    const generateBtn = this.container.querySelector('#generate-btn');
    if (!generateBtn) return;
    
    const hasText = this.currentText.trim().length > 0;
    const hasBraille = this.currentBraille.length > 0;
    
    generateBtn.disabled = !hasText || !hasBraille;
    
    if (hasText && hasBraille) {
      generateBtn.textContent = '🚀 Generate STL File';
      generateBtn.className = 'btn btn-primary';
    } else if (hasText && !hasBraille) {
      generateBtn.textContent = '🔤 Translate to Braille First';
      generateBtn.className = 'btn btn-secondary';
    } else {
      generateBtn.textContent = '📝 Enter Text Above';
      generateBtn.className = 'btn btn-disabled';
    }
  }

  async translateToBraille() {
    if (!this.currentText.trim()) {
      this.showError('Please enter some text to translate');
      return;
    }

    const translateBtn = this.container.querySelector('#translate-btn');
    const originalText = translateBtn?.textContent || '🔤 Translate to Braille';
    
    try {
      if (translateBtn) {
        translateBtn.textContent = '🔄 Translating...';
        translateBtn.disabled = true;
      }

      console.log('🔤 Translating text to braille:', this.currentText);

      // For Phase 5, use a simple fallback translation
      // In production, this would use the liblouis worker
      this.currentBraille = this.simpleTextToBraille(this.currentText);
      
      this.updateBraillePreview();
      this.updateGenerateButton();
      
      console.log('✅ Translation complete:', this.currentBraille);

    } catch (error) {
      console.error('❌ Translation failed:', error);
      this.showError('Translation failed: ' + error.message);
    } finally {
      if (translateBtn) {
        translateBtn.textContent = originalText;
        translateBtn.disabled = false;
      }
    }
  }

  simpleTextToBraille(text) {
    // Simple ASCII to braille mapping for Phase 5 demo
    const brailleMap = {
      'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋', 'g': '⠛', 'h': '⠓',
      'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕', 'p': '⠏',
      'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞', 'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭',
      'y': '⠽', 'z': '⠵', ' ': '⠀', '.': '⠲', ',': '⠂', '?': '⠦', '!': '⠖'
    };

    const lines = text.toLowerCase().split('\n').slice(0, 4); // Max 4 lines
    return lines.map(line => {
      return Array.from(line.slice(0, 30)) // Max ~30 chars per line
        .map(char => brailleMap[char] || '⠀')
        .join('');
    }).filter(line => line.length > 0);
  }

  updateBraillePreview() {
    const previewElement = this.container.querySelector('#braille-preview');
    const statsElement = this.container.querySelector('#braille-stats');
    
    if (!previewElement || !statsElement) return;
    
    if (this.currentBraille.length === 0) {
      previewElement.innerHTML = '<span class="placeholder">Braille characters will appear here...</span>';
      statsElement.textContent = '0 characters, 0 dots';
      return;
    }

    // Display braille lines
    const brailleHTML = this.currentBraille.map((line, index) => {
      return `<div class="braille-line">
        <span class="line-number">${index + 1}:</span>
        <span class="braille-text">${line}</span>
        <span class="line-length">(${line.length} chars)</span>
      </div>`;
    }).join('');

    previewElement.innerHTML = brailleHTML;

    // Calculate statistics
    const totalChars = this.currentBraille.reduce((sum, line) => sum + line.length, 0);
    const totalDots = this.currentBraille.reduce((sum, line) => {
      return sum + Array.from(line).reduce((lineSum, char) => {
        const code = char.charCodeAt(0);
        if (code >= 0x2800 && code <= 0x28FF) {
          const pattern = code - 0x2800;
          let dots = 0;
          for (let i = 0; i < 6; i++) {
            if (pattern & (1 << i)) dots++;
          }
          return lineSum + dots;
        }
        return lineSum;
      }, 0);
    }, 0);

    statsElement.textContent = `${totalChars} characters, ${totalDots} dots`;
  }

  startGeneration() {
    this.updateSettings();
    
    if (!this.currentBraille || this.currentBraille.length === 0) {
      this.showError('Please translate text to braille first');
      return;
    }

    console.log('🚀 Starting STL generation...');
    console.log('Input:', this.currentBraille);
    console.log('Settings:', this.settings);

    // Emit generate event with data
    this.dispatchEvent(new CustomEvent('generate', {
      detail: {
        brailleLines: this.currentBraille,
        shapeType: this.settings.shape_type,
        settings: this.settings,
        originalText: this.currentText
      }
    }));
  }

  showError(message) {
    // Remove existing error
    const existingError = this.container.querySelector('.error-message');
    if (existingError) {
      existingError.remove();
    }

    // Create new error
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
      <span class="error-icon">⚠️</span>
      <span class="error-text">${message}</span>
      <button class="error-close">×</button>
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

  showSuccess(message) {
    // Remove existing success
    const existingSuccess = this.container.querySelector('.success-message');
    if (existingSuccess) {
      existingSuccess.remove();
    }

    // Create new success
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `
      <span class="success-icon">✅</span>
      <span class="success-text">${message}</span>
    `;
    
    this.container.appendChild(successDiv);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.remove();
      }
    }, 3000);
  }

  setWorkerManager(workerManager) {
    this.workerManager = workerManager;
    console.log('🔗 BrailleInput connected to WorkerManager');
  }

  // Advanced translation using liblouis worker (for future implementation)
  async translateWithLiblouis(text) {
    if (!this.workerManager) {
      throw new Error('WorkerManager not available');
    }

    try {
      const brailleText = await this.workerManager.translateToBraille(text, 'en-us-g1.ctb');
      const lines = brailleText.split('\n').slice(0, 4);
      return lines.filter(line => line.trim().length > 0);
    } catch (error) {
      console.warn('Liblouis translation failed, using fallback:', error);
      return this.simpleTextToBraille(text);
    }
  }

  // Get current input state
  getCurrentInput() {
    return {
      originalText: this.currentText,
      brailleLines: this.currentBraille,
      settings: { ...this.settings }
    };
  }

  // Load example text
  loadExample(exampleType = 'hello') {
    const examples = {
      hello: 'HELLO WORLD\nBRAILLE CARD\nGENERATOR\nTEST',
      alphabet: 'ABCDEFGHIJKLM\nNOPQRSTUVWXYZ\n1234567890\n.?!',
      custom: 'CUSTOM TEXT\nFOR TESTING\nBRAILLE STL\nGENERATION'
    };

    const textInput = this.container.querySelector('#text-input');
    if (!textInput) return;
    
    textInput.value = examples[exampleType] || examples.hello;
    this.currentText = textInput.value;
    this.updateCharCount();
    this.updateGenerateButton();
    
    // Auto-translate
    setTimeout(() => {
      this.translateToBraille();
    }, 100);
  }

  // Reset form
  reset() {
    this.currentText = '';
    this.currentBraille = '';
    
    const textInput = this.container.querySelector('#text-input');
    if (textInput) {
      textInput.value = '';
    }
    
    this.updateCharCount();
    this.updateBraillePreview();
    this.updateGenerateButton();
    
    console.log('🔄 BrailleInput reset');
  }

  // Disable/enable interface
  setEnabled(enabled) {
    const inputs = this.container.querySelectorAll('input, textarea, select, button');
    inputs.forEach(input => {
      input.disabled = !enabled;
    });

    if (enabled) {
      this.container.classList.remove('disabled');
    } else {
      this.container.classList.add('disabled');
    }
  }
}

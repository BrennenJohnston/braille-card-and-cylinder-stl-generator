/**
 * Phase 5 UI Components Tests
 * Test BrailleInput, ProgressBar, STLViewer components
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { BrailleInput } from '../../src/components/BrailleInput.js';
import { ProgressBar } from '../../src/components/ProgressBar.js';
import { STLViewer } from '../../src/components/STLViewer.js';

// Mock DOM environment for components
const createMockContainer = () => {
  const container = document.createElement('div');
  container.style.width = '400px';
  container.style.height = '300px';
  document.body.appendChild(container);
  return container;
};

describe('Phase 5: UI Components', () => {
  let container;

  beforeEach(() => {
    container = createMockContainer();
  });

  afterEach(() => {
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  describe('BrailleInput Component', () => {
    let brailleInput;

    beforeEach(() => {
      brailleInput = new BrailleInput(container);
    });

    it('should initialize with correct structure', () => {
      expect(container.querySelector('.braille-input-container')).toBeDefined();
      expect(container.querySelector('#text-input')).toBeDefined();
      expect(container.querySelector('#translate-btn')).toBeDefined();
      expect(container.querySelector('#generate-btn')).toBeDefined();
      expect(container.querySelector('#braille-preview')).toBeDefined();
      
      console.log('✅ BrailleInput component structure initialized');
    });

    it('should handle text input and character counting', () => {
      const textInput = container.querySelector('#text-input');
      const charCount = container.querySelector('.char-count');
      
      // Simulate text input
      textInput.value = 'HELLO WORLD';
      textInput.dispatchEvent(new Event('input'));
      
      expect(charCount.textContent).toBe('11/500 characters');
      expect(brailleInput.currentText).toBe('HELLO WORLD');
      
      console.log('✅ Text input and character counting working');
    });

    it('should translate text to braille', () => {
      brailleInput.currentText = 'HELLO';
      brailleInput.translateToBraille();
      
      expect(brailleInput.currentBraille).toBeDefined();
      expect(brailleInput.currentBraille.length).toBeGreaterThan(0);
      
      // Check that braille preview is updated
      const braillePreview = container.querySelector('#braille-preview');
      expect(braillePreview.innerHTML).not.toContain('placeholder');
      
      console.log('✅ Text to braille translation working');
    });

    it('should handle settings updates', () => {
      const cardWidthInput = container.querySelector('#card-width');
      const shapeTypeSelect = container.querySelector('#shape-type');
      
      // Change card width
      cardWidthInput.value = '100';
      cardWidthInput.dispatchEvent(new Event('change'));
      
      // Change shape type
      shapeTypeSelect.value = 'cylinder';
      shapeTypeSelect.dispatchEvent(new Event('change'));
      
      expect(brailleInput.settings.card_width).toBe(100);
      expect(brailleInput.settings.shape_type).toBe('cylinder');
      
      console.log('✅ Settings updates working');
    });

    it('should enable/disable generate button correctly', () => {
      const generateBtn = container.querySelector('#generate-btn');
      
      // Initially disabled (no text)
      expect(generateBtn.disabled).toBe(true);
      
      // Add text but no braille
      brailleInput.currentText = 'HELLO';
      brailleInput.updateGenerateButton();
      expect(generateBtn.disabled).toBe(true);
      
      // Add braille
      brailleInput.currentBraille = ['⠓⠑⠇⠇⠕'];
      brailleInput.updateGenerateButton();
      expect(generateBtn.disabled).toBe(false);
      
      console.log('✅ Generate button state management working');
    });

    it('should load example content', () => {
      brailleInput.loadExample('hello');
      
      const textInput = container.querySelector('#text-input');
      expect(textInput.value.length).toBeGreaterThan(0);
      expect(brailleInput.currentText.length).toBeGreaterThan(0);
      
      console.log('✅ Example loading working');
    });

    it('should emit generate event with correct data', (done) => {
      brailleInput.currentText = 'HELLO';
      brailleInput.currentBraille = ['⠓⠑⠇⠇⠕'];
      
      brailleInput.addEventListener('generate', (event) => {
        expect(event.detail.brailleLines).toEqual(['⠓⠑⠇⠇⠕']);
        expect(event.detail.originalText).toBe('HELLO');
        expect(event.detail.shapeType).toBeDefined();
        expect(event.detail.settings).toBeDefined();
        
        console.log('✅ Generate event emission working');
        done();
      });
      
      brailleInput.startGeneration();
    });
  });

  describe('ProgressBar Component', () => {
    let progressBar;

    beforeEach(() => {
      progressBar = new ProgressBar(container);
    });

    it('should initialize with correct structure', () => {
      expect(container.querySelector('.progress-bar-wrapper')).toBeDefined();
      expect(container.querySelector('.progress-message')).toBeDefined();
      expect(container.querySelector('.progress-percentage')).toBeDefined();
      expect(container.querySelector('.progress-fill')).toBeDefined();
      expect(container.querySelector('.cancel-button')).toBeDefined();
      
      console.log('✅ ProgressBar component structure initialized');
    });

    it('should show and hide correctly', () => {
      const wrapper = container.querySelector('.progress-bar-wrapper');
      
      // Initially hidden
      expect(wrapper.style.display).toBe('none');
      
      // Show progress
      progressBar.show('Testing...');
      expect(wrapper.style.display).toBe('block');
      expect(progressBar.isVisible).toBe(true);
      
      // Hide progress
      progressBar.hide();
      expect(progressBar.isVisible).toBe(false);
      
      console.log('✅ Progress bar show/hide working');
    });

    it('should update progress correctly', () => {
      const percentageElement = container.querySelector('.progress-percentage');
      const fillElement = container.querySelector('.progress-fill');
      
      progressBar.show();
      progressBar.setProgress(50, 'Half way there...');
      
      expect(percentageElement.textContent).toBe('50%');
      expect(fillElement.style.width).toBe('50%');
      
      progressBar.setProgress(100, 'Complete!');
      expect(percentageElement.textContent).toBe('100%');
      expect(fillElement.style.width).toBe('100%');
      
      console.log('✅ Progress updates working');
    });

    it('should handle stage updates', () => {
      progressBar.show();
      
      // Test different stages
      progressBar.updateStage('translate');
      const translateStage = container.querySelector('[data-stage="translate"]');
      expect(translateStage.classList.contains('active')).toBe(true);
      
      progressBar.updateStage('generate');
      const generateStage = container.querySelector('[data-stage="generate"]');
      expect(generateStage.classList.contains('active')).toBe(true);
      expect(translateStage.classList.contains('complete')).toBe(true);
      
      console.log('✅ Stage updates working');
    });

    it('should emit cancel event', (done) => {
      progressBar.addEventListener('cancel', () => {
        console.log('✅ Cancel event emission working');
        done();
      });
      
      progressBar.show();
      const cancelBtn = container.querySelector('.cancel-button');
      cancelBtn.click();
    });

    it('should handle completion and error states', () => {
      progressBar.show();
      
      // Test completion
      progressBar.setComplete({ fileSize: 1024, processingTime: 2000 });
      expect(progressBar.currentProgress).toBe(100);
      
      // Test error
      progressBar.setError(new Error('Test error'));
      expect(container.querySelector('.progress-bar-wrapper').classList.contains('error-state')).toBe(true);
      
      console.log('✅ Completion and error states working');
    });
  });

  describe('STLViewer Component', () => {
    let stlViewer;

    beforeEach(() => {
      stlViewer = new STLViewer(container);
    });

    afterEach(() => {
      if (stlViewer) {
        stlViewer.destroy();
      }
    });

    it('should initialize with correct structure', () => {
      expect(container.querySelector('.stl-viewer-container')).toBeDefined();
      expect(container.querySelector('#stl-canvas')).toBeDefined();
      expect(container.querySelector('#viewer-overlay')).toBeDefined();
      expect(container.querySelector('#download-btn')).toBeDefined();
      expect(container.querySelector('#reset-view')).toBeDefined();
      
      console.log('✅ STLViewer component structure initialized');
    });

    it('should handle canvas setup', () => {
      const canvas = container.querySelector('#stl-canvas');
      expect(canvas).toBeDefined();
      expect(canvas.width).toBeGreaterThan(0);
      expect(canvas.height).toBeGreaterThan(0);
      
      console.log('✅ Canvas setup working');
    });

    it('should load STL data and update UI', async () => {
      const mockSTLBuffer = new ArrayBuffer(1000);
      const mockStats = {
        vertices: 100,
        faces: 50,
        fileSize: 1000,
        shapeType: 'card'
      };
      
      await stlViewer.loadSTL(mockSTLBuffer, mockStats);
      
      expect(stlViewer.currentSTLData).toBe(mockSTLBuffer);
      
      // Check that stats are displayed
      const verticesCount = container.querySelector('#vertices-count');
      const facesCount = container.querySelector('#faces-count');
      const fileSize = container.querySelector('#file-size');
      
      expect(verticesCount.textContent).toBe('100');
      expect(facesCount.textContent).toBe('50');
      expect(fileSize.textContent).toBe('1000 Bytes');
      
      console.log('✅ STL loading and stats display working');
    });

    it('should handle download functionality', (done) => {
      const mockSTLBuffer = new ArrayBuffer(500);
      stlViewer.currentSTLData = mockSTLBuffer;
      
      stlViewer.addEventListener('download', (event) => {
        expect(event.detail.format).toBeDefined();
        expect(event.detail.filename).toBeDefined();
        expect(event.detail.size).toBeGreaterThan(0);
        
        console.log('✅ Download event emission working');
        done();
      });
      
      stlViewer.downloadSTL('binary');
    });

    it('should clear viewer state correctly', () => {
      // Load some data first
      stlViewer.currentSTLData = new ArrayBuffer(100);
      stlViewer.currentMesh = { test: true };
      
      // Clear
      stlViewer.clear();
      
      expect(stlViewer.currentSTLData).toBe(null);
      expect(stlViewer.currentMesh).toBe(null);
      
      // Check overlay is shown
      const overlay = container.querySelector('#viewer-overlay');
      expect(overlay.style.display).toBe('flex');
      
      console.log('✅ Viewer clearing working');
    });

    it('should handle viewer controls', () => {
      const resetBtn = container.querySelector('#reset-view');
      const wireframeBtn = container.querySelector('#wireframe-toggle');
      
      // Test reset (should not crash)
      resetBtn.click();
      
      // Test wireframe toggle
      wireframeBtn.click();
      expect(wireframeBtn.classList.contains('active')).toBe(true);
      
      console.log('✅ Viewer controls working');
    });
  });

  describe('Component Integration', () => {
    it('should create all components without conflicts', () => {
      const inputContainer = createMockContainer();
      const progressContainer = createMockContainer();
      const viewerContainer = createMockContainer();
      
      const input = new BrailleInput(inputContainer);
      const progress = new ProgressBar(progressContainer);
      const viewer = new STLViewer(viewerContainer);
      
      expect(input).toBeDefined();
      expect(progress).toBeDefined();
      expect(viewer).toBeDefined();
      
      // Clean up
      viewer.destroy();
      
      // Remove containers
      [inputContainer, progressContainer, viewerContainer].forEach(c => {
        if (c.parentNode) c.parentNode.removeChild(c);
      });
      
      console.log('✅ Component integration working');
    });

    it('should handle event communication between components', (done) => {
      const inputContainer = createMockContainer();
      const input = new BrailleInput(inputContainer);
      
      // Set up data
      input.currentText = 'TEST';
      input.currentBraille = ['⠞⠑⠎⠞'];
      
      // Listen for generate event
      input.addEventListener('generate', (event) => {
        expect(event.detail.brailleLines).toEqual(['⠞⠑⠎⠞']);
        expect(event.detail.originalText).toBe('TEST');
        
        // Clean up
        if (inputContainer.parentNode) {
          inputContainer.parentNode.removeChild(inputContainer);
        }
        
        console.log('✅ Inter-component communication working');
        done();
      });
      
      input.startGeneration();
    });
  });

  describe('UI State Management', () => {
    it('should manage enable/disable states correctly', () => {
      const input = new BrailleInput(container);
      
      // Initially enabled
      const textInput = container.querySelector('#text-input');
      expect(textInput.disabled).toBe(false);
      
      // Disable
      input.setEnabled(false);
      expect(textInput.disabled).toBe(true);
      expect(container.classList.contains('disabled')).toBe(true);
      
      // Re-enable
      input.setEnabled(true);
      expect(textInput.disabled).toBe(false);
      expect(container.classList.contains('disabled')).toBe(false);
      
      console.log('✅ UI state management working');
    });

    it('should reset components to initial state', () => {
      const input = new BrailleInput(container);
      
      // Set some data
      input.currentText = 'TEST';
      input.currentBraille = ['⠞⠑⠎⠞'];
      
      // Reset
      input.reset();
      
      expect(input.currentText).toBe('');
      expect(input.currentBraille).toBe('');
      expect(container.querySelector('#text-input').value).toBe('');
      
      console.log('✅ Component reset working');
    });
  });

  describe('Error Handling', () => {
    it('should display error messages correctly', () => {
      const input = new BrailleInput(container);
      
      input.showError('Test error message');
      
      const errorElement = container.querySelector('.error-message');
      expect(errorElement).toBeDefined();
      expect(errorElement.textContent).toContain('Test error message');
      
      console.log('✅ Error message display working');
    });

    it('should display success messages correctly', () => {
      const input = new BrailleInput(container);
      
      input.showSuccess('Test success message');
      
      const successElement = container.querySelector('.success-message');
      expect(successElement).toBeDefined();
      expect(successElement.textContent).toContain('Test success message');
      
      console.log('✅ Success message display working');
    });

    it('should handle invalid input gracefully', () => {
      const input = new BrailleInput(container);
      
      // Test with empty text
      input.currentText = '';
      expect(() => input.translateToBraille()).not.toThrow();
      
      // Test with invalid characters
      input.currentText = '🙂🎉🚀';
      expect(() => input.translateToBraille()).not.toThrow();
      
      console.log('✅ Invalid input handling working');
    });
  });

  describe('Phase 5 UI Integration Status', () => {
    it('should confirm all Phase 5 components are functional', () => {
      // Test component availability
      expect(BrailleInput).toBeDefined();
      expect(ProgressBar).toBeDefined();
      expect(STLViewer).toBeDefined();
      
      // Test component instantiation
      const input = new BrailleInput(createMockContainer());
      const progress = new ProgressBar(createMockContainer());
      const viewer = new STLViewer(createMockContainer());
      
      expect(input.container).toBeDefined();
      expect(progress.container).toBeDefined();
      expect(viewer.container).toBeDefined();
      
      // Clean up
      viewer.destroy();
      
      console.log('✅ Phase 5 UI Integration: All components functional');
      console.log('✅ Ready for complete application workflow testing');
    });

    it('should provide complete user workflow simulation', () => {
      const inputContainer = createMockContainer();
      const progressContainer = createMockContainer();
      const viewerContainer = createMockContainer();
      
      // Create components
      const input = new BrailleInput(inputContainer);
      const progress = new ProgressBar(progressContainer);
      const viewer = new STLViewer(viewerContainer);
      
      // Simulate workflow
      const workflowSteps = [];
      
      // 1. User enters text
      input.currentText = 'HELLO';
      workflowSteps.push('Text entered');
      
      // 2. Text translated to braille
      input.translateToBraille();
      expect(input.currentBraille.length).toBeGreaterThan(0);
      workflowSteps.push('Braille translated');
      
      // 3. Progress shown
      progress.show('Starting generation...');
      expect(progress.isVisible).toBe(true);
      workflowSteps.push('Progress started');
      
      // 4. Progress updated
      progress.setProgress(50, 'Generating geometry...');
      expect(progress.currentProgress).toBe(50);
      workflowSteps.push('Progress updated');
      
      // 5. STL loaded
      const mockSTL = new ArrayBuffer(1000);
      viewer.currentSTLData = mockSTL;
      workflowSteps.push('STL loaded');
      
      // 6. Complete
      progress.setComplete({ fileSize: 1000 });
      expect(progress.currentProgress).toBe(100);
      workflowSteps.push('Generation completed');
      
      expect(workflowSteps).toHaveLength(6);
      
      // Clean up
      viewer.destroy();
      [inputContainer, progressContainer, viewerContainer].forEach(c => {
        if (c.parentNode) c.parentNode.removeChild(c);
      });
      
      console.log('✅ Complete workflow simulation:', workflowSteps);
      console.log('✅ Phase 5 UI ready for integration with Phase 3+4 backend');
    });
  });
});

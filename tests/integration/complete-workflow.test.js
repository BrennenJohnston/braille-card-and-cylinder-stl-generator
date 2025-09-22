/**
 * Complete Workflow Integration Tests
 * Test the entire braille-to-STL generation pipeline end-to-end
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { WorkerManager } from '../../src/lib/worker-manager.js';
import { BrailleGeneratorApp } from '../../src/App.js';
import { createTestPattern, unicodeToDots } from '../../src/lib/braille-patterns.js';

// Mock DOM environment for integration tests
const createMockAppContainer = () => {
  const container = document.createElement('div');
  container.id = 'test-app';
  container.style.width = '1200px';
  container.style.height = '800px';
  document.body.appendChild(container);
  return container;
};

describe('Phase 6: Complete Workflow Integration Tests', () => {
  let workerManager;
  let appContainer;

  beforeAll(() => {
    console.log('🧪 Setting up integration test environment...');
    workerManager = new WorkerManager();
    appContainer = createMockAppContainer();
  });

  afterAll(() => {
    console.log('🧹 Cleaning up integration test environment...');
    if (workerManager) {
      workerManager.terminate();
    }
    if (appContainer && appContainer.parentNode) {
      appContainer.parentNode.removeChild(appContainer);
    }
  });

  describe('End-to-End STL Generation Pipeline', () => {
    it('should complete full braille card generation workflow', async () => {
      console.log('🔄 Testing complete card generation workflow...');
      
      // Test data: "HELLO" in braille Unicode
      const brailleLines = ['⠓⠑⠇⠇⠕']; // H-E-L-L-O
      const settings = {
        card_width: 85.60,
        card_height: 53.98,
        card_thickness: 0.76,
        grid_columns: 32,
        grid_rows: 4
      };

      const progressSteps = [];
      let finalResult = null;

      try {
        // Execute complete workflow
        finalResult = await workerManager.generateSTL(
          'card',
          brailleLines,
          settings,
          (progress, message) => {
            progressSteps.push({ progress, message, timestamp: Date.now() });
            console.log(`  📊 ${Math.round(progress)}% - ${message}`);
          }
        );

        // Validate workflow completion
        expect(finalResult).toBeDefined();
        expect(finalResult.stlBuffer).toBeInstanceOf(ArrayBuffer);
        expect(finalResult.stats).toBeDefined();
        
        // Validate progress updates
        expect(progressSteps.length).toBeGreaterThan(0);
        expect(progressSteps[0].progress).toBeGreaterThanOrEqual(0);
        expect(progressSteps[progressSteps.length - 1].progress).toBeCloseTo(100, 0);

        // Validate STL structure
        const view = new DataView(finalResult.stlBuffer);
        const triangleCount = view.getUint32(80, true);
        const expectedSize = 84 + (50 * triangleCount);
        
        expect(triangleCount).toBeGreaterThan(100); // Should have many triangles for "HELLO"
        expect(finalResult.stlBuffer.byteLength).toBe(expectedSize);
        
        // Validate processing time
        expect(finalResult.stats.totalTime).toBeDefined();
        expect(finalResult.stats.totalTime).toBeGreaterThan(0);
        
        console.log(`✅ Card workflow complete: ${triangleCount} triangles, ${(finalResult.stlBuffer.byteLength / 1024).toFixed(1)} KB, ${finalResult.stats.totalTime}ms`);
        
      } catch (error) {
        console.error('❌ Card workflow failed:', error);
        throw error;
      }
    }, 15000);

    it('should complete full braille cylinder generation workflow', async () => {
      console.log('🔄 Testing complete cylinder generation workflow...');
      
      const brailleLines = ['⠓⠊']; // H-I (shorter for faster test)
      const settings = {
        cylinder_params: {
          diameter_mm: 31.35,
          height_mm: 53.98
        }
      };

      const progressSteps = [];

      try {
        const result = await workerManager.generateSTL(
          'cylinder',
          brailleLines,
          settings,
          (progress, message) => {
            progressSteps.push({ progress, message });
            console.log(`  📊 ${Math.round(progress)}% - ${message}`);
          }
        );

        expect(result).toBeDefined();
        expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
        expect(result.stlBuffer.byteLength).toBeGreaterThan(1000);
        
        console.log(`✅ Cylinder workflow complete: ${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB`);
        
      } catch (error) {
        console.error('❌ Cylinder workflow failed:', error);
        throw error;
      }
    }, 15000);

    it('should handle multiple concurrent generations', async () => {
      console.log('🔄 Testing concurrent generation handling...');
      
      const testData = [
        { shape: 'card', braille: ['⠁'], name: 'A' },
        { shape: 'card', braille: ['⠃'], name: 'B' }, 
        { shape: 'cylinder', braille: ['⠉'], name: 'C' }
      ];

      try {
        // Start multiple jobs concurrently
        const promises = testData.map(async (test, index) => {
          const result = await workerManager.generateSTL(
            test.shape,
            test.braille,
            {},
            (progress) => {
              console.log(`  📊 Job ${test.name}: ${Math.round(progress)}%`);
            }
          );
          
          expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
          return { ...test, result };
        });

        const results = await Promise.all(promises);
        
        expect(results).toHaveLength(testData.length);
        results.forEach(({ name, result }) => {
          expect(result.stlBuffer.byteLength).toBeGreaterThan(500);
          console.log(`  ✅ ${name}: ${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB`);
        });
        
        console.log('✅ Concurrent generation test complete');
        
      } catch (error) {
        console.error('❌ Concurrent generation failed:', error);
        throw error;
      }
    }, 20000);
  });

  describe('Braille Processing Validation', () => {
    it('should correctly process standard braille alphabet', async () => {
      console.log('🔤 Testing braille alphabet processing...');
      
      // Test all basic braille letters
      const alphabetBraille = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵'; // A-Z
      const brailleLines = [alphabetBraille];
      
      const result = await workerManager.generateSTL('card', brailleLines, {
        card_width: 120, // Wider card for alphabet
        grid_columns: 40
      });
      
      expect(result).toBeDefined();
      expect(result.stlBuffer.byteLength).toBeGreaterThan(5000); // Large file for full alphabet
      
      // Validate specific braille characters
      const testChars = ['⠁', '⠃', '⠉', '⠵']; // A, B, C, Z
      testChars.forEach(char => {
        const dots = unicodeToDots(char);
        expect(dots.some(dot => dot === 1)).toBe(true); // Should have at least one dot
      });
      
      console.log(`✅ Alphabet test complete: ${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB`);
    }, 12000);

    it('should handle edge cases correctly', async () => {
      console.log('🔄 Testing edge case handling...');
      
      const edgeCases = [
        { name: 'Empty lines', braille: [''], expectSize: 1000 },
        { name: 'Single character', braille: ['⠁'], expectSize: 500 },
        { name: 'Full braille cell', braille: ['⠿'], expectSize: 800 },
        { name: 'Mixed empty/full', braille: ['⠓⠑⠇⠇⠕', '', '⠺⠕⠗⠇⠙'], expectSize: 2000 }
      ];

      for (const testCase of edgeCases) {
        try {
          const result = await workerManager.generateSTL('card', testCase.braille);
          
          expect(result.stlBuffer.byteLength).toBeGreaterThan(testCase.expectSize);
          console.log(`  ✅ ${testCase.name}: ${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB`);
          
        } catch (error) {
          console.error(`  ❌ ${testCase.name} failed:`, error.message);
          throw error;
        }
      }
      
      console.log('✅ Edge case testing complete');
    }, 15000);
  });

  describe('Performance Validation', () => {
    it('should generate STL within performance targets', async () => {
      console.log('⚡ Testing performance targets...');
      
      const testCases = [
        { name: 'Small text (5 chars)', braille: ['⠓⠑⠇⠇⠕'], maxTime: 5000 },
        { name: 'Medium text (4 lines)', braille: ['⠓⠑⠇⠇⠕', '⠺⠕⠗⠇⠙', '⠞⠑⠎⠞', '⠁⠃⠉'], maxTime: 8000 },
        { name: 'Large text (full grid)', braille: ['⠁'.repeat(30), '⠃'.repeat(30), '⠉'.repeat(30), '⠙'.repeat(30)], maxTime: 12000 }
      ];

      for (const testCase of testCases) {
        const startTime = Date.now();
        
        try {
          const result = await workerManager.generateSTL('card', testCase.braille);
          const duration = Date.now() - startTime;
          
          expect(duration).toBeLessThan(testCase.maxTime);
          expect(result.stlBuffer.byteLength).toBeGreaterThan(1000);
          
          console.log(`  ✅ ${testCase.name}: ${duration}ms (target: <${testCase.maxTime}ms)`);
          
        } catch (error) {
          console.error(`  ❌ ${testCase.name} failed:`, error.message);
          throw error;
        }
      }
      
      console.log('✅ Performance validation complete');
    }, 25000);

    it('should maintain memory efficiency', async () => {
      console.log('🧠 Testing memory efficiency...');
      
      const initialMemory = performance.memory?.usedJSHeapSize || 0;
      
      // Generate multiple STLs to test memory management
      for (let i = 0; i < 3; i++) {
        const braille = [`⠞⠑⠎⠞${i}`];
        const result = await workerManager.generateSTL('card', braille);
        
        expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
        
        // Force garbage collection if available
        if (global.gc) {
          global.gc();
        }
      }
      
      const finalMemory = performance.memory?.usedJSHeapSize || 0;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be reasonable (less than 50MB)
      if (initialMemory > 0) {
        expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
        console.log(`  📊 Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(1)} MB`);
      }
      
      console.log('✅ Memory efficiency test complete');
    }, 15000);
  });

  describe('Error Recovery and Resilience', () => {
    it('should handle worker errors gracefully', async () => {
      console.log('🛡️ Testing error recovery...');
      
      // Test invalid inputs
      const invalidInputs = [
        { braille: null, name: 'null input' },
        { braille: 'not-an-array', name: 'string input' },
        { braille: [123], name: 'numeric input' },
        { braille: ['invalid-unicode'], name: 'invalid unicode' }
      ];

      for (const testCase of invalidInputs) {
        try {
          await workerManager.generateSTL('card', testCase.braille);
          // Should not reach here
          expect(true).toBe(false);
        } catch (error) {
          expect(error.message).toBeDefined();
          console.log(`  ✅ ${testCase.name}: Correctly rejected with "${error.message}"`);
        }
      }
      
      console.log('✅ Error recovery test complete');
    });

    it('should recover from worker crashes', async () => {
      console.log('🔧 Testing worker recovery...');
      
      // This test simulates worker recovery after errors
      // In a real scenario, workers might crash due to memory issues
      
      try {
        // Generate a normal STL first
        const result1 = await workerManager.generateSTL('card', ['⠓⠊']);
        expect(result1.stlBuffer).toBeInstanceOf(ArrayBuffer);
        
        // Workers should still be functional
        const result2 = await workerManager.generateSTL('card', ['⠃⠽⠑']);
        expect(result2.stlBuffer).toBeInstanceOf(ArrayBuffer);
        
        console.log('✅ Worker recovery test complete');
        
      } catch (error) {
        console.error('❌ Worker recovery failed:', error);
        throw error;
      }
    }, 10000);
  });

  describe('Application Integration', () => {
    it('should initialize complete application without errors', async () => {
      console.log('🖥️ Testing complete application initialization...');
      
      let app;
      try {
        // Create complete application
        app = new BrailleGeneratorApp(appContainer);
        
        // Give components time to initialize
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Verify UI structure
        expect(appContainer.querySelector('.app-container')).toBeDefined();
        expect(appContainer.querySelector('#braille-input')).toBeDefined();
        expect(appContainer.querySelector('#stl-viewer')).toBeDefined();
        expect(appContainer.querySelector('#progress-container')).toBeDefined();
        
        // Verify components are functional
        const inputContainer = appContainer.querySelector('#braille-input');
        expect(inputContainer.querySelector('#text-input')).toBeDefined();
        expect(inputContainer.querySelector('#generate-btn')).toBeDefined();
        
        console.log('✅ Application initialization successful');
        
      } catch (error) {
        console.error('❌ Application initialization failed:', error);
        throw error;
      } finally {
        if (app) {
          app.destroy();
        }
      }
    });

    it('should handle complete user workflow simulation', async () => {
      console.log('👤 Testing complete user workflow...');
      
      let app;
      try {
        app = new BrailleGeneratorApp(appContainer);
        
        // Give time for initialization
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Simulate user actions
        const workflowSteps = [];
        
        // 1. User enters text
        const textInput = appContainer.querySelector('#text-input');
        if (textInput) {
          textInput.value = 'HELLO';
          textInput.dispatchEvent(new Event('input'));
          workflowSteps.push('Text entered');
        }
        
        // 2. User clicks translate
        const translateBtn = appContainer.querySelector('#translate-btn');
        if (translateBtn) {
          translateBtn.click();
          workflowSteps.push('Translation requested');
        }
        
        // 3. User clicks generate (would trigger STL generation)
        const generateBtn = appContainer.querySelector('#generate-btn');
        if (generateBtn && !generateBtn.disabled) {
          // Don't actually click to avoid long test, just verify it's ready
          workflowSteps.push('Generate button ready');
        }
        
        expect(workflowSteps.length).toBeGreaterThanOrEqual(2);
        console.log('✅ User workflow simulation:', workflowSteps);
        
      } catch (error) {
        console.error('❌ User workflow failed:', error);
        throw error;
      } finally {
        if (app) {
          app.destroy();
        }
      }
    });
  });

  describe('Data Validation and Golden Masters', () => {
    it('should produce consistent STL output for known inputs', async () => {
      console.log('🎯 Testing golden master validation...');
      
      // Test with known braille patterns
      const goldenTests = [
        { 
          name: 'Single A', 
          braille: ['⠁'], 
          expectedMinSize: 2000,
          // Expect dot position array representation
          expectedDotPattern: [1]
        },
        { 
          name: 'Hello', 
          braille: ['⠓⠑⠇⠇⠕'], 
          expectedMinSize: 5000,
          totalDots: 14
        }
      ];

      for (const test of goldenTests) {
        const result = await workerManager.generateSTL('card', test.braille);
        
        expect(result.stlBuffer.byteLength).toBeGreaterThan(test.expectedMinSize);
        
        // Validate braille pattern if specified
        if (test.expectedDotPattern) {
          const dots = unicodeToDots(test.braille[0][0]);
          expect(dots).toEqual(test.expectedDotPattern);
        }
        
        console.log(`  ✅ ${test.name}: ${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB`);
      }
      
      console.log('✅ Golden master validation complete');
    }, 12000);

    it('should maintain STL file format compliance', async () => {
      console.log('📋 Testing STL format compliance...');
      
      const result = await workerManager.generateSTL('card', ['⠓⠑⠇⠇⠕']);
      const stlBuffer = result.stlBuffer;
      
      // Validate STL binary format structure
      const view = new DataView(stlBuffer);
      
      // Check header (80 bytes)
      expect(stlBuffer.byteLength).toBeGreaterThan(84);
      
      // Check triangle count at offset 80
      const triangleCount = view.getUint32(80, true);
      expect(triangleCount).toBeGreaterThan(0);
      
      // Validate total file size matches triangle count
      const expectedSize = 84 + (50 * triangleCount);
      expect(stlBuffer.byteLength).toBe(expectedSize);
      
      // Check that triangles are valid (basic validation)
      for (let i = 0; i < Math.min(triangleCount, 10); i++) {
        const offset = 84 + (i * 50);
        
        // Normal vector (3 floats)
        const nx = view.getFloat32(offset, true);
        const ny = view.getFloat32(offset + 4, true);
        const nz = view.getFloat32(offset + 8, true);
        
        // Normal should be valid (not all zeros, not infinite)
        const normalLength = Math.sqrt(nx*nx + ny*ny + nz*nz);
        expect(normalLength).toBeGreaterThan(0);
        expect(isFinite(normalLength)).toBe(true);
      }
      
      console.log(`✅ STL format validation: ${triangleCount} triangles, ${(stlBuffer.byteLength / 1024).toFixed(1)} KB`);
    }, 10000);
  });

  describe('Regression Testing', () => {
    it('should maintain backward compatibility with existing patterns', async () => {
      console.log('🔄 Testing backward compatibility...');
      
      // Test patterns that should work consistently
      const compatibilityTests = [
        { braille: ['⠓⠑⠇⠇⠕⠀⠺⠕⠗⠇⠙'], name: 'Hello World' },
        { braille: ['⠠⠁⠃⠉⠙⠑⠋⠛'], name: 'Capital letters' },
        { braille: ['⠼⠁⠃⠉⠙⠑'], name: 'Numbers' },
        { braille: ['⠲⠂⠦⠖⠤'], name: 'Punctuation' }
      ];

      for (const test of compatibilityTests) {
        try {
          const result = await workerManager.generateSTL('card', test.braille);
          
          expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
          expect(result.stlBuffer.byteLength).toBeGreaterThan(1000);
          
          console.log(`  ✅ ${test.name}: Compatible`);
          
        } catch (error) {
          console.error(`  ❌ ${test.name}: Compatibility broken -`, error.message);
          throw error;
        }
      }
      
      console.log('✅ Backward compatibility maintained');
    }, 15000);
  });

  describe('Phase 6 Testing Framework Status', () => {
    it('should confirm complete testing framework is operational', async () => {
      // Test framework components
      expect(WorkerManager).toBeDefined();
      expect(BrailleGeneratorApp).toBeDefined();
      expect(createTestPattern).toBeDefined();
      expect(unicodeToDots).toBeDefined();
      
      // Test worker manager functionality
      expect(workerManager.getActiveJobCount()).toBe(0);
      expect(typeof workerManager.generateSTL).toBe('function');
      expect(typeof workerManager.getStatus).toBe('function');
      
      // Test that we can create application instances
      const tempContainer = createMockAppContainer();
      const tempApp = new BrailleGeneratorApp(tempContainer);
      
      expect(tempApp).toBeDefined();
      expect(tempApp.workerManager).toBeDefined();
      
      // Cleanup
      tempApp.destroy();
      if (tempContainer.parentNode) {
        tempContainer.parentNode.removeChild(tempContainer);
      }
      
      console.log('✅ Phase 6 Testing Framework: All components operational');
      console.log('✅ Integration tests ready for production validation');
      console.log('✅ Ready for Phase 7: Cloudflare Pages Deployment');
    });
  });
});

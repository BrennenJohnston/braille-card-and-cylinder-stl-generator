/**
 * Performance Benchmark Tests
 * Measure and validate STL generation performance targets
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { WorkerManager } from '../../src/lib/worker-manager.js';

describe('Phase 6: Performance Benchmarks', () => {
  let workerManager;
  const benchmarkResults = [];

  beforeAll(() => {
    console.log('⚡ Setting up performance benchmarks...');
    workerManager = new WorkerManager();
  });

  afterAll(() => {
    console.log('📊 Performance benchmark summary:');
    benchmarkResults.forEach(result => {
      console.log(`  ${result.name}: ${result.duration}ms (${result.status})`);
    });
    
    if (workerManager) {
      workerManager.terminate();
    }
  });

  describe('STL Generation Performance', () => {
    it('should generate small braille cards under 3 seconds', async () => {
      const testName = 'Small Card (5 chars)';
      const startTime = performance.now();
      
      try {
        const result = await workerManager.generateSTL('card', ['⠓⠑⠇⠇⠕'], {
          card_width: 50,
          card_height: 30
        });
        
        const duration = performance.now() - startTime;
        const target = 3000; // 3 seconds
        
        expect(duration).toBeLessThan(target);
        expect(result.stlBuffer.byteLength).toBeGreaterThan(1000);
        
        benchmarkResults.push({
          name: testName,
          duration: Math.round(duration),
          target,
          status: duration < target ? '✅ PASS' : '❌ FAIL',
          fileSize: result.stlBuffer.byteLength
        });
        
        console.log(`⚡ ${testName}: ${Math.round(duration)}ms (target: <${target}ms)`);
        
      } catch (error) {
        benchmarkResults.push({
          name: testName,
          duration: -1,
          target: 3000,
          status: '❌ ERROR',
          error: error.message
        });
        throw error;
      }
    }, 10000);

    it('should generate medium braille cards under 8 seconds', async () => {
      const testName = 'Medium Card (4 lines)';
      const startTime = performance.now();
      
      try {
        const brailleLines = [
          '⠓⠑⠇⠇⠕⠀⠺⠕⠗⠇⠙', // HELLO WORLD
          '⠃⠗⠁⠊⠇⠇⠑⠀⠉⠁⠗⠙', // BRAILLE CARD  
          '⠛⠑⠝⠑⠗⠁⠞⠕⠗',      // GENERATOR
          '⠞⠑⠎⠞⠊⠝⠛'           // TESTING
        ];
        
        const result = await workerManager.generateSTL('card', brailleLines);
        
        const duration = performance.now() - startTime;
        const target = 8000; // 8 seconds
        
        expect(duration).toBeLessThan(target);
        expect(result.stlBuffer.byteLength).toBeGreaterThan(5000);
        
        benchmarkResults.push({
          name: testName,
          duration: Math.round(duration),
          target,
          status: duration < target ? '✅ PASS' : '❌ FAIL',
          fileSize: result.stlBuffer.byteLength
        });
        
        console.log(`⚡ ${testName}: ${Math.round(duration)}ms (target: <${target}ms)`);
        
      } catch (error) {
        benchmarkResults.push({
          name: testName,
          duration: -1,
          target: 8000,
          status: '❌ ERROR',
          error: error.message
        });
        throw error;
      }
    }, 15000);

    it('should generate cylinders under 6 seconds', async () => {
      const testName = 'Cylinder Generation';
      const startTime = performance.now();
      
      try {
        const result = await workerManager.generateSTL('cylinder', ['⠓⠑⠇⠇⠕'], {
          cylinder_params: {
            diameter_mm: 31.35,
            height_mm: 53.98
          }
        });
        
        const duration = performance.now() - startTime;
        const target = 6000; // 6 seconds
        
        expect(duration).toBeLessThan(target);
        expect(result.stlBuffer.byteLength).toBeGreaterThan(2000);
        
        benchmarkResults.push({
          name: testName,
          duration: Math.round(duration),
          target,
          status: duration < target ? '✅ PASS' : '❌ FAIL',
          fileSize: result.stlBuffer.byteLength
        });
        
        console.log(`⚡ ${testName}: ${Math.round(duration)}ms (target: <${target}ms)`);
        
      } catch (error) {
        benchmarkResults.push({
          name: testName,
          duration: -1,
          target: 6000,
          status: '❌ ERROR',
          error: error.message
        });
        throw error;
      }
    }, 12000);
  });

  describe('Memory Performance', () => {
    it('should maintain stable memory usage during generation', async () => {
      console.log('🧠 Testing memory stability...');
      
      const initialMemory = performance.memory?.usedJSHeapSize || 0;
      const memoryReadings = [];
      
      try {
        // Generate multiple STLs and track memory
        for (let i = 0; i < 3; i++) {
          const beforeGeneration = performance.memory?.usedJSHeapSize || 0;
          
          await workerManager.generateSTL('card', [`⠞⠑⠎⠞⠀${i}`]);
          
          const afterGeneration = performance.memory?.usedJSHeapSize || 0;
          const memoryDelta = afterGeneration - beforeGeneration;
          
          memoryReadings.push({
            iteration: i,
            before: beforeGeneration,
            after: afterGeneration,
            delta: memoryDelta
          });
          
          // Force cleanup
          if (global.gc) {
            global.gc();
          }
        }
        
        // Analyze memory stability
        if (initialMemory > 0) {
          const maxDelta = Math.max(...memoryReadings.map(r => r.delta));
          const avgDelta = memoryReadings.reduce((sum, r) => sum + r.delta, 0) / memoryReadings.length;
          
          // Memory growth should be reasonable
          expect(maxDelta).toBeLessThan(100 * 1024 * 1024); // Less than 100MB per generation
          
          console.log(`  📊 Max memory delta: ${(maxDelta / 1024 / 1024).toFixed(1)} MB`);
          console.log(`  📊 Avg memory delta: ${(avgDelta / 1024 / 1024).toFixed(1)} MB`);
        }
        
        console.log('✅ Memory stability test complete');
        
      } catch (error) {
        console.error('❌ Memory test failed:', error);
        throw error;
      }
    }, 15000);
  });

  describe('Framework Performance Targets', () => {
    it('should meet all Phase 6 performance requirements', () => {
      console.log('🎯 Validating Phase 6 performance targets...');
      
      // Analyze benchmark results
      const passedTests = benchmarkResults.filter(r => r.status.includes('PASS'));
      const failedTests = benchmarkResults.filter(r => r.status.includes('FAIL'));
      const errorTests = benchmarkResults.filter(r => r.status.includes('ERROR'));
      
      console.log(`📊 Performance Summary:`);
      console.log(`  ✅ Passed: ${passedTests.length}`);
      console.log(`  ❌ Failed: ${failedTests.length}`);
      console.log(`  🔥 Errors: ${errorTests.length}`);
      
      // All tests should pass for Phase 6 completion
      expect(failedTests.length).toBe(0);
      expect(errorTests.length).toBe(0);
      expect(passedTests.length).toBeGreaterThan(0);
      
      // Calculate average performance
      if (passedTests.length > 0) {
        const avgDuration = passedTests.reduce((sum, r) => sum + r.duration, 0) / passedTests.length;
        console.log(`  ⚡ Average generation time: ${Math.round(avgDuration)}ms`);
        
        // Should meet framework target of <30 seconds (30,000ms) - we're aiming much better
        expect(avgDuration).toBeLessThan(10000); // 10 seconds average
      }
      
      console.log('✅ All Phase 6 performance targets met!');
      console.log('✅ Framework performance requirements satisfied');
    });
  });
});

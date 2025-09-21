/**
 * Phase 3 Worker Architecture Tests
 * Test worker initialization, communication, and job management
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WorkerManager } from '../../src/lib/worker-manager.js';

// Mock worker implementation for testing
class MockWorker extends EventTarget {
  constructor(url) {
    super();
    this.url = url;
    this.terminated = false;
    
    // Simulate worker initialization with delay
    setTimeout(() => {
      if (!this.terminated) {
        this.dispatchEvent(new MessageEvent('message', {
          data: { 
            type: 'READY', 
            id: 'init-job-id',
            capabilities: { test: true } 
          }
        }));
      }
    }, 10);
  }

  postMessage(data) {
    if (this.terminated) return;
    
    console.log('MockWorker received message:', data);
    
    // Simulate worker responses
    setTimeout(() => {
      if (this.terminated) return;
      
      switch (data.type) {
        case 'INIT':
          this.dispatchEvent(new MessageEvent('message', {
            data: { 
              type: 'READY', 
              id: data.id,
              capabilities: { 
                brailleGeneration: true,
                stlExport: true 
              } 
            }
          }));
          break;
          
        case 'GENERATE_CARD':
          // Validate input data
          if (!data.data || !data.data.brailleLines || !Array.isArray(data.data.brailleLines)) {
            setTimeout(() => {
              this.dispatchEvent(new MessageEvent('message', {
                data: { 
                  type: 'ERROR', 
                  id: data.id,
                  error: { message: 'Invalid brailleLines provided' }
                }
              }));
            }, 1);
            break;
          }
          
          // Simulate progress updates
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: { 
                type: 'PROGRESS', 
                id: data.id, 
                progress: 50,
                message: 'Processing...' 
              }
            }));
          }, 5);
          
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: { 
                type: 'GENERATION_COMPLETE', 
                id: data.id, 
                result: {
                  geometry: {
                    positions: new Float32Array([0, 0, 0, 1, 1, 1]),
                    normals: new Float32Array([0, 1, 0, 0, 1, 0])
                  },
                  stats: { vertices: 2, faces: 1 }
                }
              }
            }));
          }, 20);
          break;
          
        case 'GENERATE_CYLINDER':
          // Validate input data
          if (!data.data || !data.data.brailleLines || !Array.isArray(data.data.brailleLines)) {
            setTimeout(() => {
              this.dispatchEvent(new MessageEvent('message', {
                data: { 
                  type: 'ERROR', 
                  id: data.id,
                  error: { message: 'Invalid brailleLines provided' }
                }
              }));
            }, 1);
            break;
          }
          
          // Simulate cylinder generation
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: { 
                type: 'PROGRESS', 
                id: data.id, 
                progress: 60,
                message: 'Generating cylinder...' 
              }
            }));
          }, 5);
          
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: { 
                type: 'GENERATION_COMPLETE', 
                id: data.id, 
                result: {
                  geometry: {
                    positions: new Float32Array([0, 0, 0, 1, 1, 1, 2, 2, 2]),
                    normals: new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0])
                  },
                  stats: { vertices: 3, faces: 1 }
                }
              }
            }));
          }, 15);
          break;
          
        case 'EXPORT_STL':
          setTimeout(() => {
            const mockSTLBuffer = new ArrayBuffer(100);
            this.dispatchEvent(new MessageEvent('message', {
              data: { 
                type: 'EXPORT_COMPLETE', 
                id: data.id, 
                result: {
                  data: mockSTLBuffer,
                  format: 'binary',
                  stats: { estimatedFileSize: 100 }
                }
              }
            }));
          }, 10);
          break;
          
        case 'GET_STATUS':
          this.dispatchEvent(new MessageEvent('message', {
            data: { 
              type: 'STATUS', 
              id: data.id, 
              status: { 
                initialized: true, 
                busy: false 
              } 
            }
          }));
          break;
      }
    }, 1);
  }

  terminate() {
    this.terminated = true;
    console.log('MockWorker terminated');
  }
}

// Mock the Worker constructor
global.Worker = MockWorker;

// Mock URL constructor for worker imports
global.URL = class MockURL {
  constructor(url, base) {
    this.href = url;
  }
};

describe('Phase 3: Worker Architecture', () => {
  let workerManager;

  beforeEach(() => {
    workerManager = new WorkerManager();
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (workerManager) {
      workerManager.terminate();
    }
  });

  describe('WorkerManager', () => {
    it('should initialize correctly', () => {
      expect(workerManager).toBeDefined();
      expect(workerManager.getActiveJobCount()).toBe(0);
      expect(workerManager.areWorkersReady()).toBe(false);
    });

    it('should create and initialize geometry worker', async () => {
      const worker = await workerManager.getWorker('geometry');
      
      expect(worker).toBeDefined();
      expect(worker).toBeInstanceOf(MockWorker);
      expect(workerManager.areWorkersReady()).toBe(true);
    }, 10000);

    it('should reuse existing workers', async () => {
      const worker1 = await workerManager.getWorker('geometry');
      const worker2 = await workerManager.getWorker('geometry');
      
      expect(worker1).toBe(worker2);
    });

    it('should generate unique job IDs', () => {
      const id1 = workerManager.generateJobId();
      const id2 = workerManager.generateJobId();
      
      expect(id1).not.toBe(id2);
      expect(typeof id1).toBe('string');
      expect(id1.length).toBeGreaterThan(10);
    });
  });

  describe('Worker Communication', () => {
    it('should handle worker progress updates', async () => {
      const progressUpdates = [];
      
      const result = await workerManager.generateSTL(
        'card',
        ['⠇'], // Simple test braille line (dots 1,2,3)
        {},
        (progress, message) => {
          progressUpdates.push({ progress, message });
        }
      );
      
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates[0].progress).toBeGreaterThanOrEqual(0);
      expect(result).toBeDefined();
      expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
    }, 5000);

    it('should handle worker initialization timeout', async () => {
      // Mock a worker that never responds
      global.Worker = class TimeoutWorker extends EventTarget {
        constructor() {
          super();
          // Never send READY message
        }
        postMessage() {}
        terminate() {}
      };

      const timeoutManager = new WorkerManager();
      
      await expect(timeoutManager.getWorker('geometry')).rejects.toThrow('timeout');
      
      timeoutManager.terminate();
      
      // Restore mock
      global.Worker = MockWorker;
    }, 12000);

    it('should handle worker errors gracefully', async () => {
      // Mock a worker that sends error
      global.Worker = class ErrorWorker extends EventTarget {
        postMessage(data) {
          setTimeout(() => {
            if (data.type === 'INIT') {
              this.dispatchEvent(new MessageEvent('message', {
                data: { 
                  type: 'ERROR', 
                  id: data.id,
                  error: { message: 'Test error' }
                }
              }));
            }
          }, 1);
        }
        terminate() {}
      };

      const errorManager = new WorkerManager();
      
      await expect(errorManager.getWorker('geometry')).rejects.toThrow('Test error');
      
      errorManager.terminate();
      
      // Restore mock
      global.Worker = MockWorker;
    });
  });

  describe('Job Management', () => {
    it('should track active jobs', async () => {
      expect(workerManager.getActiveJobCount()).toBe(0);
      
      // Start a job but don't await it yet
      const jobPromise = workerManager.generateSTL('card', ['⠓⠊'], {}); // "HI" in braille
      
      // Give it a moment to register
      await new Promise(resolve => setTimeout(resolve, 5));
      
      // Should have active job now
      expect(workerManager.getActiveJobCount()).toBeGreaterThan(0);
      
      // Wait for job to complete
      await jobPromise;
      
      // Should be back to 0
      expect(workerManager.getActiveJobCount()).toBe(0);
    }, 3000);

    it('should provide worker status', async () => {
      // Initialize a worker first
      await workerManager.getWorker('geometry');
      
      const status = await workerManager.getStatus();
      
      expect(status).toBeDefined();
      expect(status.workers).toBeDefined();
      expect(status.activeJobs).toBeDefined();
      expect(status.totalJobs).toBeGreaterThan(0);
    }, 3000);

    it('should handle job cancellation', async () => {
      // This test is more complex since we need to simulate a long-running job
      // For now, just test that cancelJob method exists and doesn't crash
      expect(typeof workerManager.cancelJob).toBe('function');
      
      // Should not crash when cancelling non-existent job
      workerManager.cancelJob('non-existent-job');
    });
  });

  describe('STL Generation Workflow', () => {
    it('should complete full STL generation workflow', async () => {
      const brailleLines = ['⠓⠑']; // "HE" in braille

      const progressSteps = [];
      
      const result = await workerManager.generateSTL(
        'card',
        brailleLines,
        { card_width: 50, card_height: 30 },
        (progress, message) => {
          progressSteps.push({ progress, message });
          console.log(`Progress: ${progress}% - ${message}`);
        }
      );

      // Verify result structure
      expect(result).toBeDefined();
      expect(result.stlBuffer).toBeInstanceOf(ArrayBuffer);
      expect(result.format).toBe('binary');
      expect(result.stats).toBeDefined();
      expect(result.stats.fileSize).toBeGreaterThan(0);

      // Verify progress updates
      expect(progressSteps.length).toBeGreaterThan(0);
      
      console.log(`✅ Full workflow test complete: ${result.stats.fileSize} bytes STL generated`);
    }, 5000);

    it('should validate input data', async () => {
      // Test with invalid braille lines
      await expect(workerManager.generateSTL('card', null)).rejects.toThrow();
      await expect(workerManager.generateSTL('card', 'not-an-array')).rejects.toThrow();
    });

    it('should handle different shape types', async () => {
      const brailleLines = ['⠓⠑⠇']; // "HEL" in braille
      
      // Test card generation
      const cardResult = await workerManager.generateSTL('card', brailleLines);
      expect(cardResult).toBeDefined();
      
      // Test cylinder generation  
      const cylinderResult = await workerManager.generateSTL('cylinder', brailleLines);
      expect(cylinderResult).toBeDefined();
    }, 3000);
  });

  describe('Memory Management', () => {
    it('should properly terminate workers', () => {
      const initialWorkerCount = workerManager.workers.size;
      
      workerManager.terminate();
      
      expect(workerManager.getActiveJobCount()).toBe(0);
      expect(workerManager.areWorkersReady()).toBe(false);
    });

    it('should clean up after job completion', async () => {
      const result = await workerManager.generateSTL('card', ['⠓⠑⠇'], {}); // "HEL" in braille
      
      expect(result).toBeDefined();
      expect(workerManager.getActiveJobCount()).toBe(0);
    });
  });
});
